using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace WhisperAttackServerCommand
{
    public class VA_Plugin
    {
        private static bool _isRunning = true;
        private static TcpListener _listener = null;
        private static IPAddress _listenerIpAddress = IPAddress.Parse("127.0.0.1");
        private static int _listenerPort = 65433;

        public static string VA_DisplayName()
        {
            return "WhisperAttack";
        }

        public static string VA_DisplayInfo()
        {
            return "WhisperAttack Server Command plugin (v1.2.2)";
        }

        public static Guid VA_Id()
        {
            return new Guid("{1AD02372-145E-4143-BBBE-AC7575595C24}");
        }

        public static void VA_StopCommand()
        {
        }

        public static void VA_Init1(dynamic vaProxy)
        {
            // Configuration for connecting to the WhisperAttack server.
            string server = "127.0.0.1";
            int port = 65432;

            try
            {
                using (TcpClient client = new TcpClient(server, port))
                using (NetworkStream stream = client.GetStream())
                {
                    vaProxy.WriteToLog("Connected to WhisperAttack server", "blue");
                }
            }
            catch (Exception ex)
            {
                vaProxy.WriteToLog($"Failed to connect to WhisperAttack server: {ex.Message}", "red");
            }

            loadConfiguration(vaProxy);
            StartCommandListener(vaProxy);
        }

        public static void VA_Invoke1(dynamic vaProxy)
        {
            string server = "127.0.0.1";
            int port = 65432;

            string contextinput = vaProxy.Context;

            try
            {
                using (TcpClient client = new TcpClient(server, port))
                using (NetworkStream stream = client.GetStream())
                {
                    switch (contextinput)
                    {
                        case "Start Whisper Recording":
                            {
                                string command = "start"; // Command sent to whisper server
                                byte[] data = Encoding.ASCII.GetBytes(command);
                                stream.Write(data, 0, data.Length);
                                vaProxy.WriteToLog("Start WhisperAttack recording", "grey");
                                break;
                            }

                        case "Stop Whisper Recording":
                            {
                                string command = "stop"; // Command sent to whisper server
                                byte[] data = Encoding.ASCII.GetBytes(command);
                                stream.Write(data, 0, data.Length);
                                vaProxy.WriteToLog("Stop WhisperAttack recording", "grey");
                                break;
                            }
                    }
                }
            }
            catch (Exception ex)
            {
                vaProxy.WriteToLog($"WhisperAttack server command error: {ex.Message}", "red");
            }
        }

        public static void VA_Exit1(dynamic vaProxy)
        {
            _isRunning = false;
            _listener.Stop();

            string server = "127.0.0.1";
            int port = 65432;

            using (TcpClient client = new TcpClient(server, port))
            using (NetworkStream stream = client.GetStream())
            {
                string command = "shutdown"; // Command sent to whisper server
                byte[] data = Encoding.ASCII.GetBytes(command);
                stream.Write(data, 0, data.Length);
            }
        }

        private static void loadConfiguration(dynamic vaProxy)
        {
            string settingsFile = "Apps\\WhisperAttackServerCommand\\settings.cfg";
            string currentDir = Directory.GetCurrentDirectory();
            string filePath = Path.Combine(currentDir, settingsFile);

            // Read the configuration file, if it exists, in the format key=value
            if (!File.Exists(filePath))
            {
                vaProxy.WriteToLog($"WhisperAttack configuration file ({filePath}) not found, using defaults", "orange");
                return;
            }

            try
            {
                foreach (var line in File.ReadAllLines(filePath))
                {
                    // Trim whitespace and skip empty or comment lines
                    var trimmed = line.Trim();
                    if (string.IsNullOrEmpty(trimmed) || trimmed.StartsWith("#"))
                        continue;

                    // Split into key and value at the first '='
                    var parts = trimmed.Split(new[] { '=' }, 2);
                    if (parts.Length == 2)
                    {
                        string key = parts[0].Trim();
                        string value = parts[1].Trim();

                        
                        if (!string.IsNullOrEmpty(key))
                        {
                            if (key.Equals("listener_address"))
                            {
                                if (!IPAddress.TryParse(value, out IPAddress ipAddress))
                                {
                                    vaProxy.WriteToLog($"Invalid listener ip address {value}, using default 127.0.0.1", "red");
                                }
                                else
                                {
                                    _listenerIpAddress = ipAddress;
                                }
                            }
                            else if (key.Equals("listener_port"))
                            {
                                try
                                {

                                    _listenerPort = int.Parse(value);
                                }
                                catch
                                {
                                    vaProxy.WriteToLog($"Invalid listener port: {value}, using default 65433", "red");
                                }
                            }
                            else
                            {
                                vaProxy.WriteToLog($"Ignoring unknown WhisperAttack configuration {key}={value}", "orange");
                            }
                        }
                    }
                    else
                    {
                        vaProxy.WriteToLog($"Skipping invalid configuration: {line}", "orange");
                    }
                }
            }
            catch (Exception ex)
            {
                vaProxy.WriteToLog($"Error reading WhisperAttack configuration file: {ex.Message}", "red");
            }
        }

        private static async Task StartCommandListener(dynamic vaProxy)
        {
            vaProxy.WriteToLog($"Starting WhisperAttack listener on {_listenerIpAddress}:{_listenerPort}", "blue");
            
            try
            {
                _listener = new TcpListener(new IPEndPoint(_listenerIpAddress, _listenerPort));
                _listener.Start();
                
                vaProxy.WriteToLog($"WhisperAttack listener started", "blue");

                while (_isRunning)
                {
                    await HandleWhisperAttackCommand(vaProxy, await _listener.AcceptTcpClientAsync());
                }
            }
            catch (Exception ex)
            {
                vaProxy.WriteToLog($"Error starting WhisperAttack listener: {ex.Message}", "red");
            }
        }

        private static async Task HandleWhisperAttackCommand(dynamic vaProxy, TcpClient client)
        {
            await Task.Yield();

            using (NetworkStream stream = client.GetStream())
            {
                try
                {
                    byte[] buffer = new byte[1024];
                    int bytesRead = await stream.ReadAsync(buffer, 0, buffer.Length);
                    string receivedMessage = Encoding.UTF8.GetString(buffer, 0, bytesRead);

                    vaProxy.WriteToLog($"Received WhisperAttack command: '{receivedMessage}'", "grey");

                    if (vaProxy.Command.Exists(receivedMessage))
                    {
                        vaProxy.Command.Execute(receivedMessage, true, true);
                    }
                    else
                    {
                        vaProxy.WriteToLog($"Command '{receivedMessage}' not found", "orange");
                    }
                }
                catch (Exception ex)
                {
                    vaProxy.WriteToLog($"Error reading command: {ex.Message}", "red");
                }
            }
        }
    }
}
