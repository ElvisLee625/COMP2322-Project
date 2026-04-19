import socket
import threading
import os
import datetime
import time
from email.utils import formatdate, parsedate_to_datetime


log_File = os.path.join(os.path.dirname(os.path.abspath(__file__)),"webServer.log")
root_Location = os.path.dirname(os.path.abspath(__file__))

def log_Write (client_IP, requested_File, response):
    current_Time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_File, "a", encoding="utf-8") as log:
        log.write(f"{client_IP} | {current_Time} | {requested_File} | {response} \n")


def client_Request (request):
    sentences = request.split('\r\n')
    if not sentences or not sentences[0]:
        return None, None, {}, None
    request_sentence = sentences[0].strip()
    parts = request_sentence.split()
    if len(parts) != 3:
        return None, None, {}, None
    command = parts[0]
    file = parts[1]
    version = parts[2]
    header = {}
    for request_sentence in sentences[1:]:
        if request_sentence.strip() == '':
            break
        if ':' in request_sentence:
            key, value = request_sentence.split(':', 1)
            header[key.strip().lower()] = value.strip()
    return command, file, header, version






def Server_Response (client_Socket, client_Address):
    while True:
        try:
            client_Socket.settimeout(15)
            request_Data = bytes()
            while True:
                received_Data = client_Socket.recv(8192)
                if not received_Data:
                    break
                request_Data += received_Data
                if bytes('\r\n\r\n', 'ascii') in request_Data:
                    break
            if not request_Data:
                break

            request_String = request_Data.decode('utf-8', errors='ignore')
        except:
            break
        
        command, file, header, version = client_Request(request_String)
        if command not in ['GET', 'HEAD']:
            response_Log = "400 Bad Request"
            response = "HTTP/1.1 400 Bad Request\r\nContent-Type:text/html\r\nConnection: close\r\n\r\n<h1>400 Bad Request</h1>"
            client_Socket.sendall(response.encode('utf-8'))
            log_Write(client_Address, file, response_Log)
            break
        
        if file == "/" or file == '':
            file = '/index.html'
        if "?" in file:
            file = file.split('?')[0]

        file_Path = os.path.normpath(os.path.join(root_Location, file.lstrip('/')))



        true_File_Path = os.path.abspath(file_Path)
        true_Root_Location = os.path.abspath(root_Location)

        if not true_File_Path.startswith(true_Root_Location) or not os.access(file_Path, os.R_OK):
            response_Log = "403 Forbidden"
            response = "HTTP/1.1 403 Forbidden\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n<h1>403 Forbidden</h1>"
            client_Socket.sendall(response.encode('utf-8'))
            log_Write(client_Address, file, response_Log)
            break


        if not os.path.exists(file_Path) or not os.path.isfile(file_Path):
            response_Log = "404 Not Found"
            response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n<h1>404 Not Found</h1>"
            client_Socket.sendall(response.encode('utf-8'))
            log_Write(client_Address, file, response_Log)
            break

        



        last_Modified = get_Last_Modified(file_Path)
        if_Modified = header.get('if-modified-since')
        modified = False
        if if_Modified and command == "GET":
            try:
                Time = parsedate_to_datetime(if_Modified)
                if os.path.getmtime(file_Path) <= Time.timestamp() + 1:
                    modified = True
            except:
                pass

        if modified:
            response_Log = "304 Not Modified"
            response = f"HTTP/1.1 304 Not Modified\r\nLast_Modified:{last_Modified}\r\nConnection: close\r\n\r\n<h1>304 Not Modified</h1>"
            client_Socket.sendall(response.encode('utf-8'))
            log_Write(client_Address, file, response_Log)
            break


        file_Type = get_File_Type(file_Path)
        file_Size = os.path.getsize(file_Path)
        response = "200 OK"
        response_Header = f"HTTP/1.1 200 OK\r\nContent-Type:{file_Type}\r\nContent-Length:{file_Size}\r\nLast_Modified:{last_Modified}\r\nServer: 127.0.0.1\r\n"
        
        connection = header.get('connection', 'keep-alive' if version.startswith('HTTP/1.1') else 'close').lower()
        keep_alive = (connection == 'keep-alive')
        response_Header += "Connection: {}\r\n\r\n".format('keep-alive' if keep_alive else 'close')
        client_Socket.sendall(response_Header.encode('utf-8'))
        log_Write(client_Address, file, response_Header)
        if command == 'GET':
            with open(file_Path, 'rb') as f:
                while True:
                    data = f.read(4096)
                    if not data:
                        break
                    client_Socket.sendall(data)


        


        



def get_File_Type (file_Path):
    ext = os.path.splitext(file_Path)[1].lower()
    if ext in ('.html', '.htm'):
        return 'text/html'
    if ext == '.txt':
        return 'text/plain'
    if ext in ('.jpg', '.jpeg'):
        return 'image/jpeg'
    return 'application/octet-stream'

def get_Last_Modified (file_Path):
    last_Modified_time = os.path.getmtime(file_Path)
    return formatdate(timeval = last_Modified_time, localtime = False, usegmt = True)
            






def main():
    open(log_File, "w").close()
    print(" Log file created: ", log_File)
    server_Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_Port = 8080
    server_IP = '127.0.0.1'
    server_Socket.bind((server_IP, server_Port))
    server_Socket.listen(5)

    while True:
        client_Socket, client_Address = server_Socket.accept()
        thread = threading.Thread(target = Server_Response, args = (client_Socket, client_Address))
        thread.start()

if __name__ == "__main__":
    main()