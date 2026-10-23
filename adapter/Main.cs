using System;
using System.Collections.Concurrent;
using System.Net;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using Rage;
using LSPD_First_Response.Mod.API;
using LSPD_First_Response;

namespace PatrolAIBackupAdapter
{
    // Plugins em Plugins/LSPDFR sao carregados pelo LSPDFR ao entrar em servico.
    public class Main : Plugin
    {
        private const string BaseUrl = "http://127.0.0.1:8765";
        private volatile bool alive;
        private volatile bool onDuty;
        private int workerStarted;
        private readonly ConcurrentQueue<BackupJob> queue = new ConcurrentQueue<BackupJob>();
        private static readonly JavaScriptSerializer Json = new JavaScriptSerializer();
        private DateTime lastBackup = DateTime.MinValue;

        private sealed class BackupJob { public string Id; public int Code; public string Type; public string Service; }

        public override void Initialize()
        {
            alive = true;
            Functions.OnOnDutyStateChanged += DutyChanged;
            Game.LogTrivial("[PatrolAI-Adapter] Inicializado; aguardando servico.");
            GameFiber.StartNew(GameLoop);
        }

        private void DutyChanged(bool duty)
        {
            onDuty = duty;
            Game.LogTrivial("[PatrolAI-Adapter] Em servico=" + duty);
            if (duty && Interlocked.Exchange(ref workerStarted, 1) == 0)
                System.Threading.Tasks.Task.Run(() => PollLoop());
        }

        private void GameLoop()
        {
            while (alive)
            {
                GameFiber.Yield();
                BackupJob job;
                if (!queue.TryDequeue(out job)) continue;
                bool success = false;
                string error = "";
                try
                {
                    if (!onDuty) throw new InvalidOperationException("Policial fora de servico");
                    if (DateTime.UtcNow - lastBackup < TimeSpan.FromSeconds(35))
                        throw new InvalidOperationException("Aguarde 35 segundos entre pedidos de reforco");
                    var ped = Game.LocalPlayer.Character;
                    if (ped == null || !ped.Exists()) throw new InvalidOperationException("Policial indisponivel");
                    // Preserva comportamento de perseguicao ja testado pelo usuario.
                    // Nao muda apoio policial existente nesta atualizacao.
                    if (job.Type == "request_service")
                    {
                        EBackupUnitType unit;
                        if (job.Service == "ambulance") unit = EBackupUnitType.Ambulance;
                        else if (job.Service == "prisoner_transport") unit = EBackupUnitType.PrisonerTransport;
                        else throw new InvalidOperationException("Servico sem adaptador: " + job.Service);
                        Functions.RequestBackup(ped.Position, EBackupResponseType.Code2, unit);
                    }
                    else
                    {
                        Functions.RequestBackup(ped.Position, EBackupResponseType.Pursuit, EBackupUnitType.LocalUnit);
                    }
                    lastBackup = DateTime.UtcNow;
                    success = true;
                    Game.LogTrivial("[PatrolAI-Adapter] Chamada RequestBackup executada id=" + job.Id + " codigo=" + job.Code);
                }
                catch (Exception e)
                {
                    error = e.ToString();
                    Game.LogTrivial("[PatrolAI-Adapter] Falha de reforco id=" + job.Id + " " + error);
                }
                // A comunicacao HTTP nunca deve bloquear a fibra do GTA.
                string id = job.Id;
                bool ok = success;
                string message = error.Length > 240 ? error.Substring(0, 240) : error;
                System.Threading.Tasks.Task.Run(() => Report(id, ok, message));
            }
        }

        private void PollLoop()
        {
            while (alive)
            {
                try
                {
                    if (onDuty)
                    {
                        string body = Get("/adapter/next");
                        if (!String.IsNullOrWhiteSpace(body))
                        {
                            var job = Json.Deserialize<BackupJobPayload>(body);
                            if (job != null && !String.IsNullOrWhiteSpace(job.id))
                                queue.Enqueue(new BackupJob { Id = job.id, Code = job.code, Type = job.type ?? "request_backup", Service = job.service ?? "" });
                        }
                    }
                }
                catch (WebException) { /* Bridge nao iniciado; tentar novamente */ }
                catch (Exception e) { Game.LogTrivial("[PatrolAI-Adapter] Poll: " + e.Message); }
                Thread.Sleep(750);
            }
        }
        private sealed class BackupJobPayload { public string id {get;set;} public int code {get;set;} public string type {get;set;} public string service {get;set;} }
        private static string Get(string path)
        {
            var req = (HttpWebRequest)WebRequest.Create(BaseUrl + path);
            req.Timeout = 2000;
            using (var response = (HttpWebResponse)req.GetResponse())
            {
                if (response.StatusCode == HttpStatusCode.NoContent) return "";
                using (var reader = new StreamReader(response.GetResponseStream())) return reader.ReadToEnd();
            }
        }
        private static void Report(string id, bool success, string error)
        {
            try
            {
                var req = (HttpWebRequest)WebRequest.Create(BaseUrl + "/action-result/" + id);
                req.Method = "POST"; req.ContentType = "application/json";
                req.Timeout = 5000;
                byte[] data = Encoding.UTF8.GetBytes(Json.Serialize(new {success, error}));
                req.ContentLength = data.Length;
                using (var s = req.GetRequestStream()) s.Write(data, 0, data.Length);
                using (var response = req.GetResponse()) { }
            }
            catch (Exception e) { Game.LogTrivial("[PatrolAI-Adapter] Falha ACK " + id + ": " + e); }
        }
        public override void Finally()
        {
            alive = false; onDuty = false;
            Functions.OnOnDutyStateChanged -= DutyChanged;
            Game.LogTrivial("[PatrolAI-Adapter] Finalizado.");
        }
    }
}
