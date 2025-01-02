import threading
import socket
import sounddevice as sd
import soundfile as sf
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
)

# Modify the following to your liking
audio_file = r".\sample.wav"
duration = 10  # Maximum duration in seconds

# DO NOT MODIFY ANYTHING BELOW THIS LINE....

server_ready_event = threading.Event()  # Event to signal when server is ready

def socket_server(stop_event):
    HOST = '127.0.0.1'  # Localhost
    PORT = 65432        # Port to listen on

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            logging.info('Socket server started, waiting for stop signal...')
            server_ready_event.set()  # Signal that the server is ready

            while not stop_event.is_set():
                try:
                    conn, addr = s.accept()
                    with conn:
                        logging.info(f'Connected by {addr}')
                        data = conn.recv(1024)
                        if data.strip() == b'stop':
                            logging.info('Stop signal received.')
                            stop_event.set()
                        else:
                            logging.warning('Unknown command received.')
                except socket.error as e:
                    logging.error(f'Socket error: {e}')
    except Exception as e:
        logging.error(f'Failed to start socket server: {e}')
        stop_event.set()

def main():
    stop_event = threading.Event()
    # Run the socket server in a separate thread
    server_thread = threading.Thread(target=socket_server, args=(stop_event,))
    server_thread.start()

    # Wait until the server is ready
    server_ready_event.wait()

    # Optimal settings for Whisper
    fs = 16000     # Whisper expects 16 kHz sample rate
    channels = 1   # Mono audio
    subtype = 'FLOAT'  # Record audio in float32 format (required by Whisper)

    logging.info("Recording started...")
    try:
        with sf.SoundFile(audio_file, mode='w', samplerate=fs, channels=channels, subtype=subtype) as file:
            with sd.InputStream(samplerate=fs, channels=channels, dtype='float32', callback=lambda indata, frames, time_info, status: file.write(indata)):
                start_time = time.time()
                while True:
                    if stop_event.is_set():
                        # Stop recording if stop signal received
                        break
                    elif time.time() - start_time >= duration:
                        # Maximum duration reached
                        logging.info("Maximum recording duration reached.")
                        break
                    else:
                        # Sleep briefly to prevent high CPU usage
                        time.sleep(0.05)
    except Exception as e:
        logging.error(f'An error occurred during recording: {e}')
    finally:
        logging.info("Recording finished. Closing audio file.")

    # Wait for the server thread to finish
    server_thread.join()
    logging.info("Socket server closed.")

if __name__ == '__main__':
    main()