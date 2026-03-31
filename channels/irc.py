import socket, threading, random

_running = False
_sock = None
_sock_lock = threading.Lock()
_last_message = ''
_msg_lock = threading.Lock()
_channel = None
_connected = False
_joined = False
_state_lock = threading.Lock()
_outbox = []
_outbox_lock = threading.Lock()

def _set_last(msg):
    global _last_message
    with _msg_lock:
        if _last_message == '':
            _last_message = msg
        else:
            _last_message = _last_message + ' | ' + msg

def getLastMessage():
    global _last_message
    with _msg_lock:
        tmp = _last_message
        _last_message = ''
        return tmp

def _set_state(connected=None, joined=None):
    global _connected, _joined
    with _state_lock:
        if connected is not None:
            _connected = connected
        if joined is not None:
            _joined = joined

def _is_ready():
    with _state_lock:
        return _connected and _joined

def _close_socket(sock=None):
    global _sock
    with _sock_lock:
        target = _sock if sock is None else sock
        if sock is None or _sock is sock:
            _sock = None
    if target is not None:
        try:
            target.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            target.close()
        except OSError:
            pass

def _send_raw(cmd):
    global _sock
    data = (cmd + '\r\n').encode('utf-8', 'ignore')
    with _sock_lock:
        sock = _sock
    if sock is None:
        return False
    try:
        sock.sendall(data)
        return True
    except OSError:
        _set_state(connected=False, joined=False)
        _close_socket(sock)
        return False

def _sanitize_text(text):
    text = str(text).replace('\r\n', '\n').replace('\r', '\n')
    parts = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        while len(line.encode('utf-8')) > 400:
            cut = line[:400]
            while len(cut.encode('utf-8')) > 400 and cut:
                cut = cut[:-1]
            parts.append(cut)
            line = line[len(cut):].lstrip()
        parts.append(line)
    if not parts:
        parts = [' ']
    return parts

def _flush_outbox():
    while _is_ready():
        with _outbox_lock:
            if not _outbox:
                return
            text = _outbox[0]
        if not _send_raw(f'PRIVMSG {_channel} :{text}'):
            return
        with _outbox_lock:
            if _outbox and _outbox[0] == text:
                _outbox.pop(0)

def _irc_loop(channel, server, port, nick):
    global _running, _sock
    sock = socket.socket()
    sock.settimeout(1.0)
    try:
        sock.connect((server, port))
    except OSError:
        _set_state(connected=False, joined=False)
        return
    with _sock_lock:
        _sock = sock
    _set_state(connected=False, joined=False)
    _send_raw(f'NICK {nick}')
    _send_raw(f'USER {nick} 0 * :{nick}')
    buffer = ''
    while _running:
        try:
            data = sock.recv(4096)
        except socket.timeout:
            continue
        except OSError:
            break
        if not data:
            break
        buffer += data.decode(errors='ignore')
        while '\r\n' in buffer:
            line, buffer = buffer.split('\r\n', 1)
            if not line:
                continue
            if line.startswith('PING'):
                token = line.split(' ', 1)[1] if ' ' in line else ':ping'
                _send_raw(f'PONG {token}')
                continue
            parts = line.split()
            if len(parts) > 1 and parts[1] == '001':
                _set_state(connected=True, joined=False)
                _send_raw(f'JOIN {channel}')
                continue
            if len(parts) > 1 and parts[1] == 'JOIN':
                prefix = parts[0][1:] if parts[0].startswith(':') else ''
                joined_nick = prefix.split('!', 1)[0]
                target = parts[2] if len(parts) > 2 else ''
                if target.startswith(':'):
                    target = target[1:]
                if joined_nick == nick and target == channel:
                    _set_state(joined=True)
                    _flush_outbox()
                continue
            if line.startswith(':') and ' PRIVMSG ' in line:
                try:
                    prefix, trailing = line[1:].split(' PRIVMSG ', 1)
                    sender = prefix.split('!', 1)[0]
                    if ' :' not in trailing:
                        continue
                    msg = trailing.split(' :', 1)[1]
                    _set_last(f'{sender}: {msg}')
                except Exception:
                    pass
    _set_state(connected=False, joined=False)
    _close_socket(sock)

def start_irc(channel, server='irc.libera.chat', port=6667, nick='mettaclaw'):
    global _running, _channel
    stop_irc()
    nick = f'{nick}{random.randint(1000, 9999)}'
    _channel = channel
    _running = True
    _set_state(connected=False, joined=False)
    t = threading.Thread(target=_irc_loop, args=(channel, server, port, nick), daemon=True)
    t.start()
    return t

def stop_irc():
    global _running
    _running = False
    _set_state(connected=False, joined=False)
    _close_socket()

def send_message(text):
    chunks = _sanitize_text(text)
    with _outbox_lock:
        _outbox.extend(chunks)
    _flush_outbox()
