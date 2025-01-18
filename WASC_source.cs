using System;
using System.Net.Sockets;
using System.Text;
using System.Collections.Generic;

namespace WhisperAttackServerCommand
{
    public class VA_Plugin
    {
        public static string VA_DisplayName()
        {
            return "WASC V0.1beta";
        }

        public static string VA_DisplayInfo()
        {
            return "Whisper Attack Server Command Native plugin";
        }

        public static Guid VA_Id()
        {
            return new Guid("{1AD02372-145E-4143-BBBE-AC7575595C24}");
        }

        static bool _stopVariableToMonitor = false;

        public static void VA_StopCommand()
        {
            _stopVariableToMonitor = true;
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
                    Console.WriteLine("Connected to the server.");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to connect to server: {ex.Message}");
            }
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
                                Console.WriteLine($"Sent: {command}");
                                break;
                            }

                        case "Stop Whisper Recording":
                            {
                                string command = "stop"; // Command sent to whisper server
                                byte[] data = Encoding.ASCII.GetBytes(command);
                                stream.Write(data, 0, data.Length);
                                Console.WriteLine($"Sent: {command}");
                                break;
                            }
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"WASC server command error: {ex.Message}");
            }
        }

        public static void VA_Exit1(dynamic vaProxy)
        {
            string server = "127.0.0.1";
            int port = 65432;

            try
            {
                using (TcpClient client = new TcpClient(server, port))
                using (NetworkStream stream = client.GetStream())
                {
                    string command = "shutdown"; // Command sent to whisper server
                    byte[] data = Encoding.ASCII.GetBytes(command);
                    stream.Write(data, 0, data.Length);
                    Console.WriteLine($"Sent: {command}");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"WASC server shutdown error: {ex.Message}");
            }
        }
    }
}
