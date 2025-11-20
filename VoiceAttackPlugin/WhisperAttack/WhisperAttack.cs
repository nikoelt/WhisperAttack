using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace WhisperAttack
{
    public class WhisperAttackServerCommand
    {
        private static bool _isRunning = true;
        private static TcpListener _listener = null;
        private static IPAddress _listenerIpAddress = IPAddress.Parse("127.0.0.1");
        private static int _listenerPort = 65433;

        /// <summary>
        /// The plugin’s display name, required by the VoiceAttack plugin API.
        /// </summary>
        /// <returns>The display name.</returns>
        public static string VA_DisplayName()
        {
            return "WhisperAttack";
        }

        /// <summary>
        /// The plugin’s description, required by the VoiceAttack plugin API.
        /// </summary>
        /// <returns>The description.</returns>
        public static string VA_DisplayInfo()
        {
            return "WhisperAttack Server Command plugin (v1.2.2)";
        }

        /// <summary>
        /// The plugin’s GUID, required by the VoiceAttack plugin API.
        /// </summary>
        /// <returns>The GUID.</returns>
        public static Guid VA_Id()
        {
            return new Guid("{1AD02372-145E-4143-BBBE-AC7575595C24}");
        }

        /// <summary>
        /// VoiceAttack calls this when a command is run to stop all running commands.
        /// This is currently unused.
        /// </summary>
        public static void VA_StopCommand()
        {
            // no-op
        }

        /// <summary>
        /// Invoked when the plugin is loaded. This runs a connection test to see if the WhisperAttack
        /// server is currently running, and starts up the listener for receiving commands.
        /// </summary>
        /// <param name="vaProxy">The VoiceAttack proxy for calling VoiceAttack functions</param>
        public static void VA_Init1(dynamic vaProxy)
        {
            // Run a connection test to see if WhisperAttack is currently running and
            // listening for server commands.
            try
            {
                // Configuration for connecting to the WhisperAttack server.
                string server = "127.0.0.1";
                int port = 65432;

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

            LoadConfiguration(vaProxy);
            StartCommandListener(vaProxy);
        }

        /// <summary>
        /// Sends the start/stop recording commands to the WhisperAttack server.
        /// </summary>
        /// <param name="vaProxy">The VoiceAttack proxy for calling VoiceAttack functions</param>
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

        /// <summary>
        /// Send the shudown command to the WhisperAttack server when VoiceAttack exits.
        /// This will close WhisperAttack so that it is no longer running.
        /// </summary>
        /// <param name="vaProxy">The VoiceAttack proxy for calling VoiceAttack functions</param>
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

        /// <summary>
        /// Loads the configuration from the settings.cfg file in the same location as the plugin.
        /// Configuration is in the format key=value
        /// Configuration specifies the ip address and port for listening on to receive text commands.
        /// </summary>
        /// <param name="vaProxy">The VoiceAttack proxy for calling VoiceAttack functions</param>
        private static void LoadConfiguration(dynamic vaProxy)
        {
            // Get the VoiceAttack directory that contains plugins
            string voiceAttackAppsDir = vaProxy.SessionState["VA_APPS"];
            // Create the path to the WhisperAttack plugin directory and configuration file under the folder
            // that VoiceAttack keeps plugins in.
            string filePath = Path.Combine(voiceAttackAppsDir, "WhisperAttackServerCommand\\settings.cfg");

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
                    // Trim whitespace and skip empty or commented out lines
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
                                // Check if the value provided is a valid IP address
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
                                    // Check if the listener port is a valid number
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

        /// <summary>
        /// Start the TCP listener for receiving text commands.
        /// This is run as a Task so that it does not block the main plugin thread while listening.
        /// </summary>
        /// <param name="vaProxy">The VoiceAttack proxy for calling VoiceAttack functions</param>
        /// <returns></returns>
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

        /// <summary>
        /// Handler for commands received by listener and then execute the associated VoiceAttack command.
        /// Run as a Task so that it does not block the main plugin thread.
        /// </summary>
        /// <param name="vaProxy">The VoiceAttack proxy for calling VoiceAttack functions</param>
        /// <param name="client">The TCP client to read from the received command from</param>
        /// <returns></returns>
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

                    // If the command exists within the VoiceAttack profile then run it.
                    // We check for the command first so that we can log this nicely vs. the generic
                    // external command failure.
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
