using System;
using System.Collections.Generic;
using System.Collections.Concurrent;
using System.Net;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Rage;

[assembly: Rage.Attributes.Plugin("PatrolAI", Description = "COPOM contextual com IA local")]

namespace PatrolAI
{
    public static class EntryPoint
    {
        private static volatile bool running = true;
        private sealed class PendingBackup
        {
            public int Code;
            public readonly System.Threading.ManualResetEventSlim Completed = new System.Threading.ManualResetEventSlim(false);
            public bool Success;
            public string Error;
        }
        private static readonly ConcurrentQueue<PendingBackup> PendingActions = new ConcurrentQueue<PendingBackup>();
        private static DateTime lastBackup = DateTime.MinValue;
        private static readonly TimeSpan BackupCooldown = TimeSpan.FromSeconds(35);
        private static bool f6WasDown, f7WasDown;
        private static int busy = 0;
        private static readonly ConcurrentQueue<string> Notifications = new ConcurrentQueue<string>();
        private const string Url = "http://127.0.0.1:8765";
        private static readonly JavaScriptSerializer Json = new JavaScriptSerializer();

        public static void Main()
        {
            Game.DisplayNotification("~b~PatrolAI v0.5.3~s~ carregado. F7: COPOM | F6 em manutencao");
            GameFiber.StartNew(Loop);
            while (running) GameFiber.Yield();
        }

        public static void OnUnload(bool isTerminating)
        {
            running = false;
        }

        private static void Loop()
        {
            while (running)
            {
                GameFiber.Yield();
                // v0.5.3: despacho executado somente pelo plugin LSPDFR BackupAdapter.
                string notice;
                while (Notifications.TryDequeue(out notice)) Game.DisplayNotification(notice);
                bool f6 = Game.IsKeyDown(Keys.F6), f7 = Game.IsKeyDown(Keys.F7);
                if (f6 && !f6WasDown) Game.DisplayNotification("~y~PatrolAI:~s~ F6 temporariamente desativado (pedestres).");
                if (f7 && !f7WasDown) Begin("copom");
                f6WasDown = f6;
                f7WasDown = f7;
            }
        }

        private static void Begin(string mode)
        {
            if (System.Threading.Interlocked.CompareExchange(ref busy, 1, 0) != 0)
            {
                Game.DisplayNotification("~y~PatrolAI:~s~ aguarde a transmissao atual.");
                return;
            }
            string identity = "COPOM", location = "Localizacao nao identificada";
            float distance = 0;
            if (mode == "copom")
            {
                try
                {
                    Ped player = Game.LocalPlayer.Character;
                    if (player != null && player.Exists())
                    {
                        var position = player.Position;
                        var street = World.GetStreetName(position);
                        // Sempre enviar coordenadas atuais para distinguir pontos da mesma rua.
                        location = (String.IsNullOrWhiteSpace(street) ? "Rua nao identificada" : "Rua proxima: " + street)
                            + "; posicao XYZ: " + position.X.ToString("0") + ", " + position.Y.ToString("0") + ", " + position.Z.ToString("0");
                    }
                }
                catch (Exception ex)
                {
                    Game.DisplayNotification("~y~PatrolAI:~s~ localizacao indisponivel; radio continua ativo.");
                }
            }
            if (mode == "npc")
            {
                Ped player = Game.LocalPlayer.Character;
                Ped closest = null;
                float best = 4.0f;
                foreach (Ped ped in player.GetNearbyPeds(16))
                {
                    if (ped == null || !ped.Exists() || ped == player) continue;
                    float d = ped.DistanceTo(player);
                    if (d < best) { best = d; closest = ped; }
                }
                if (closest == null)
                {
                    Game.DisplayNotification("~y~PatrolAI:~s~ aproxime-se de um pedestre (até 4 metros).");
                    System.Threading.Interlocked.Exchange(ref busy, 0);
                    return;
                }
                distance = best;
                // Handles are session-scoped; entities can despawn or be recycled.
                identity = "ped-" + closest.Handle;
            }
            Dictionary<string, object> vehicleSnapshot = SelectVehicleSnapshot();
            if (vehicleSnapshot != null && Convert.ToBoolean(vehicleSnapshot["found"]))
                Game.DisplayNotification("~b~Veiculo proximo:~s~ " + vehicleSnapshot["plate"] + " (" + vehicleSnapshot["distance_m"] + "m)");
            else
                Game.DisplayNotification("~y~PatrolAI:~s~ nenhum veiculo-alvo a ate 12m; consulta por placa digitada segue disponivel.");
            Game.DisplayNotification("~b~PatrolAI local enviado:~s~ " + location);
            Game.DisplayNotification("~b~PatrolAI:~s~ preparando microfone...");
            var payload = new Dictionary<string, object> {
                {"mode", mode}, {"identity", identity}, {"location", location}, {"distance", distance}, {"vehicle", vehicleSnapshot}
            };
            // Never block the game fiber with network or inference.
            System.Threading.Tasks.Task.Run(() => NetworkInteraction(payload));
        }

        // Capture on the RPH game fiber; do not touch game entities in Task.Run.
        private static Dictionary<string, object> SelectVehicleSnapshot()
        {
            var result = new Dictionary<string, object> { {"found", false} };
            try
            {
                Ped player = Game.LocalPlayer.Character;
                if (player == null || !player.Exists()) return result;
                Vehicle current = player.CurrentVehicle;
                Vehicle bestVehicle = null;
                float best = 12.0f;
                foreach (Vehicle v in player.GetNearbyVehicles(16))
                {
                    if (v == null || !v.Exists() || v == current) continue;
                    float distance = v.DistanceTo(player);
                    if (distance < best) { best = distance; bestVehicle = v; }
                }
                if (bestVehicle != null)
                {
                    result["found"] = true;
                    result["plate"] = bestVehicle.LicensePlate ?? "";
                    result["model"] = bestVehicle.Model.Name ?? "";
                    result["distance_m"] = Math.Round(best, 1);
                }
            }
            catch (Exception ex) { Game.DisplayNotification("~y~PatrolAI:~s~ veiculo indisponivel: " + ex.Message); }
            return result;
        }

        private static void NetworkInteraction(Dictionary<string, object> payload)
        {
            try
            {
                string response = Request("POST", "/start", Json.Serialize(payload));
                var job = Json.Deserialize<Dictionary<string, object>>(response);
                string id = Convert.ToString(job["id"]);
                string previous = "";
                bool actionHandled = false;
                for (int i = 0; i < 400 && running; i++)
                {
                    System.Threading.Thread.Sleep(400);
                    var status = Json.Deserialize<Dictionary<string, object>>(Request("GET", "/status/" + id, null));
                    string state = Convert.ToString(status["state"]);
                    if (state == "action_pending" && !actionHandled)
                    {
                        actionHandled = true;
                        Notify("~b~PatrolAI:~s~ aguardando adaptador do LSPDFR...");
                        // Nao confirmar a acao aqui: BackupAdapter envia POST /action-result.
                    }
                    if (state != previous)
                    {
                        previous = state;
                        if (state == "listening") Notify("~g~Fale agora!~s~ (tempo definido no Bridge)");
                        else if (state == "thinking") Notify("~b~PatrolAI:~s~ processando...");
                    }
                    if (state == "done")
                    {
                        string reply = Convert.ToString(status["reply"]);
                        Notify("~b~PatrolAI:~s~ " + (reply.Length > 150 ? reply.Substring(0, 150) + "..." : reply));
                        return;
                    }
                    if (state == "error") { Notify("~r~PatrolAI:~s~ " + Convert.ToString(status["error"])); return; }
                }
                Notify("~y~PatrolAI:~s~ tempo limite excedido.");
            }
            catch (Exception ex)
            {
                Notify("~r~PatrolAI:~s~ falha no pedido. " + ex.Message);
                // Error also appears in the in-game notification.
            }
            finally
            {
                System.Threading.Interlocked.Exchange(ref busy, 0);
            }
        }

        private static string Request(string method, string endpoint, string body)
        {
            var req = (HttpWebRequest)WebRequest.Create(Url + endpoint);
            req.Method = method;
            req.Timeout = 10000;
            req.ReadWriteTimeout = 10000;
            if (body != null)
            {
                byte[] bytes = Encoding.UTF8.GetBytes(body);
                req.ContentType = "application/json; charset=utf-8";
                req.ContentLength = bytes.Length;
                using (var stream = req.GetRequestStream()) stream.Write(bytes, 0, bytes.Length);
            }
            using (var response = (HttpWebResponse)req.GetResponse())
            using (var reader = new System.IO.StreamReader(response.GetResponseStream(), Encoding.UTF8))
                return reader.ReadToEnd();
        }

        private static void Notify(string message)
        {
            // RPH display calls must be scheduled on the game fiber.
            Notifications.Enqueue(message);
        }
    }
}
