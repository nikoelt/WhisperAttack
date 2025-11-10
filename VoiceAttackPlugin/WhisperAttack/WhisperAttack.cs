using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;

namespace WhisperAttackServerCommand
{
    public class VA_Plugin
    {
        private static bool _isRunning = true;
        private static TcpListener _server = null;

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
            string server = "127.0.0.1"; // Localhost
            int port = 65432; // Port of the Python server

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

            vaProxy.WriteToLog("Plugin 'WhisperAttackServerCommand' initialized", "blue");
            
            StartCommandServer(vaProxy);
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
            _server.Stop();

            string server = "127.0.0.1";
            int port = 65432;

            try
            {
                using (TcpClient client = new TcpClient(server, port))
                using (NetworkStream stream = client.GetStream())
                {
                    vaProxy.WriteToLog("Sending shutdown to WhisperAttack", "blue");
                    string command = "shutdown"; // Command sent to whisper server
                    byte[] data = Encoding.ASCII.GetBytes(command);
                    stream.Write(data, 0, data.Length);
                }
            }
            catch (Exception ex)
            {
                vaProxy.WriteToLog($"WhisperAttack shutdown error: {ex.Message}", "red");
            }
        }

        public static void StartCommandServer(dynamic vaProxy)
        {
            vaProxy.WriteToLog("Starting WhisperAttack server", "blue");
            
            try
            {
                _server = new TcpListener(IPAddress.Loopback, 65433);
                _server.Start();
                vaProxy.WriteToLog("WhisperAttack server started on port 65433", "blue");

                while (_isRunning)
                {
                    using (TcpClient client = _server.AcceptTcpClient())
                    {
                        NetworkStream stream = client.GetStream();
                        byte[] buffer = new byte[1024];
                        int bytesRead = stream.Read(buffer, 0, buffer.Length);
                        string receivedMessage = Encoding.UTF8.GetString(buffer, 0, bytesRead);

                        vaProxy.WriteToLog($"WhisperAttack command: '{receivedMessage}'", "grey");

                        if (vaProxy.Command.Exists(receivedMessage))
                        {
                            vaProxy.Command.Execute(receivedMessage, true, true);
                        }
                        else
                        {
                            vaProxy.WriteToLog($"Command '{receivedMessage}' not found", "orange");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                vaProxy.WriteToLog($"Error starting WhisperAttack server: {ex.Message}", "red");
            }
            finally
            {
                _server.Stop();
            }
        }
    }
}
