using System;
using System.Collections;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;

public class TextureManager2023 : MonoBehaviour
{
    [Header("Einstellungen")]
    [SerializeField] private string ordnerName = "SpielerTexturen";
    [SerializeField] private string zielDateiName = "PlayerHead.png";

    private string ordnerPfad;
    private string hauptDateiPfad;
    private Renderer objektRenderer;
    private Texture2D geladeneTextur;

    // Der Shader-Eigenschafts-Name (Nutze "_BaseMap" für URP oder "_MainTex" für den alten Standard-Shader)
    private readonly string shaderEigenschaft = "_BaseMap"; 

    void Start()
    {
        objektRenderer = GetComponent<Renderer>();

        // Generiert den Pfad im Dokumente-Ordner des PCs
        ordnerPfad = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), ordnerName);
        hauptDateiPfad = Path.Combine(ordnerPfad, zielDateiName);

        // Ordner erstellen, falls nicht vorhanden
        if (!Directory.Exists(ordnerPfad))
        {
            Directory.CreateDirectory(ordnerPfad);
            Debug.Log($"Ordner wurde erstellt unter: {ordnerPfad}");
        }

        // Führt die Prüfung und das Laden aus
        VerarbeiteOrdner();
    }

    void VerarbeiteOrdner()
    {
        if (!Directory.Exists(ordnerPfad)) return;

        string[] dateien = Directory.GetFiles(ordnerPfad, "*.*", SearchOption.TopDirectoryOnly);

        foreach (string datei in dateien)
        {
            string dateiName = Path.GetFileName(datei);

            // Ignoriere die korrekte Hauptdatei und bereits nummerierte Backups
            if (dateiName.Equals(zielDateiName, StringComparison.OrdinalIgnoreCase) || 
                dateiName.StartsWith("PlayerHead_", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            string extension = Path.GetExtension(datei).ToLower();
            if (extension == ".png" || extension == ".jpg" || extension == ".jpeg")
            {
                RotiereAlteDateien();
                
                // Verschiebe und benenne die neue Datei um
                File.Move(datei, hauptDateiPfad);
                Debug.Log($"Neue Textur erkannt und als '{zielDateiName}' gesetzt.");
                break; 
            }
        }

        // Wenn die Datei existiert, lade sie in Unity 2023
        if (File.Exists(hauptDateiPfad))
        {
            StartCoroutine(LadeTexturAsynchron(hauptDateiPfad));
        }
    }

    void RotiereAlteDateien()
    {
        if (!File.Exists(hauptDateiPfad)) return;

        int index = 1;
        string backupPfad;

        // Sucht die nächste freie Nummer
        do
        {
            backupPfad = Path.Combine(ordnerPfad, $"PlayerHead_{index}.png");
            index++;
        } 
        while (File.Exists(backupPfad));

        File.Move(hauptDateiPfad, backupPfad);
        Debug.Log($"Alte Textur archiviert als: {Path.GetFileName(backupPfad)}");
    }

    IEnumerator LadeTexturAsynchron(string pfad)
    {
        // Unity 2023 verlangt das korrekte URI-Format für lokale Dateien
        string url = "file://" + pfad.Replace("\\", "/");

        using (UnityWebRequest request = UnityWebRequestTexture.GetTexture(url))
        {
            yield return request.SendWebRequest();

            if (request.result == UnityWebRequest.Result.ConnectionError || request.result == UnityWebRequest.Result.ProtocolError)
            {
                Debug.LogError($"Fehler beim Laden der Textur in Unity 2023: {request.error}");
            }
            else
            {
                // Wichtig für Unity 2023: Alten Textur-Speicher freigeben, um RAM-Leaks zu verhindern
                if (geladeneTextur != null) 
                {
                    Destroy(geladeneTextur);
                }

                geladeneTextur = DownloadHandlerTexture.GetContent(request);
                
                // Unity 2023 moderner Weg: Textur über die Shader-Eigenschaft zuweisen
                if (objektRenderer != null && objektRenderer.material != null)
                {
                    objektRenderer.material.SetTexture(shaderEigenschaft, geladeneTextur);
                }
            }
        }
    }

    // Speicherbereinigung beim Zerstören des Objekts
    private void OnDestroy()
    {
        if (geladeneTextur != null)
        {
            Destroy(geladeneTextur);
        }
    }
}