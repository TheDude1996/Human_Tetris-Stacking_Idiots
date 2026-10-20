using System;
using System.IO;
using UnityEngine;

#if UNITY_EDITOR
using UnityEditor; // Wird benötigt, um FBX und Textur direkt in das Unity-Projekt einzubinden
#endif

public class ModelAndTextureManager2023 : MonoBehaviour
{
    [Header("Einstellungen (Externer Ordner)")]
    [SerializeField] private string ordnerName = "SpielerTexturen";
    [SerializeField] private string zielModellName = "PlayerHead.fbx";
    [SerializeField] private string zielTexturName = "PlayerHead.png";

    [Header("Einstellungen (Unity Projektordner)")]
    [Tooltip("Der Ordner innerhalb von Assets, in den FBX und Textur kopiert werden")]
    [SerializeField] private string unityZielOrdner = "ImportedModels";

    private string ordnerPfad;
    private string modellHauptPfad;
    private string texturHauptPfad;
    private GameObject instanziiertesModell;

    void Start()
    {
        // Generiert den Pfad im Dokumente-Ordner des PCs
        ordnerPfad = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), ordnerName);
        modellHauptPfad = Path.Combine(ordnerPfad, zielModellName);
        texturHauptPfad = Path.Combine(ordnerPfad, zielTexturName);

        // Ordner erstellen, falls nicht vorhanden
        if (!Directory.Exists(ordnerPfad))
        {
            Directory.CreateDirectory(ordnerPfad);
            Debug.Log($"Ordner wurde erstellt unter: {ordnerPfad}");
        }

        // Führt die Prüfung, das Kopieren und das Laden aus
        VerarbeiteOrdner();
    }

    void VerarbeiteOrdner()
    {
        if (!Directory.Exists(ordnerPfad)) return;

        string[] dateien = Directory.GetFiles(ordnerPfad, "*.*", SearchOption.TopDirectoryOnly);

        // Schritt 1: Nach einer neuen FBX suchen
        foreach (string datei in dateien)
        {
            string dateiName = Path.GetFileName(datei);

            if (dateiName.Equals(zielModellName, StringComparison.OrdinalIgnoreCase) || 
                dateiName.StartsWith("PlayerHead_", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            string extension = Path.GetExtension(datei).ToLower();
            if (extension == ".fbx")
            {
                RotiereAlteDateien();
                
                // Verschiebe und benenne die neue FBX im externen Ordner um
                File.Move(datei, modellHauptPfad);
                Debug.Log($"Neue FBX-Datei erkannt und als '{zielModellName}' gesetzt.");
                break; 
            }
        }

        // Schritt 2: Nach einer neuen PNG/JPG suchen (falls vorhanden)
        // Aktualisiert die Dateiliste nach der FBX-Rotation
        dateien = Directory.GetFiles(ordnerPfad, "*.*", SearchOption.TopDirectoryOnly);
        foreach (string datei in dateien)
        {
            string dateiName = Path.GetFileName(datei);

            if (dateiName.Equals(zielTexturName, StringComparison.OrdinalIgnoreCase) || 
                dateiName.StartsWith("PlayerHead_", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            string extension = Path.GetExtension(datei).ToLower();
            if (extension == ".png" || extension == ".jpg" || extension == ".jpeg")
            {
                // Wenn bereits eine alte Haupttextur existiert, überschreiben oder löschen wir sie für das Backup
                if (File.Exists(texturHauptPfad))
                {
                    File.Delete(texturHauptPfad);
                }
                
                File.Move(datei, texturHauptPfad);
                Debug.Log($"Neue Textur-Datei erkannt und als '{zielTexturName}' gesetzt.");
                break;
            }
        }

        // Wenn das Modell existiert, binden wir alles ins Projekt ein
        if (File.Exists(modellHauptPfad))
        {
#if UNITY_EDITOR
            KopiereInUnityProjekt();
            LadeModellAusProjekt();
#endif
        }
    }

    void RotiereAlteDateien()
    {
        if (!File.Exists(modellHauptPfad)) return;

        int index = 1;
        string backupModellPfad;
        string backupTexturPfad;

        // Sucht die nächste freie Nummer
        do
        {
            backupModellPfad = Path.Combine(ordnerPfad, $"PlayerHead_{index}.fbx");
            backupTexturPfad = Path.Combine(ordnerPfad, $"PlayerHead_{index}.png");
            index++;
        } 
        while (File.Exists(backupModellPfad));

        // Modell rotieren
        File.Move(modellHauptPfad, backupModellPfad);

        // Zugehörige Textur rotieren (falls vorhanden)
        if (File.Exists(texturHauptPfad))
        {
            File.Move(texturHauptPfad, backupTexturPfad);
            Debug.Log($"Alte FBX & Textur archiviert unter Index {index - 1}");
        }
        else
        {
            Debug.Log($"Alte FBX archiviert als: {Path.GetFileName(backupModellPfad)}");
        }
    }

#if UNITY_EDITOR
    private void KopiereInUnityProjekt()
    {
        string projektOrdnerPfad = Path.Combine(Application.dataPath, unityZielOrdner);
        
        if (!Directory.Exists(projektOrdnerPfad))
        {
            Directory.CreateDirectory(projektOrdnerPfad);
        }

        // 1. Kopiere die Textur zuerst (Wichtig, damit Unity sie beim FBX-Import direkt findet!)
        if (File.Exists(texturHauptPfad))
        {
            string texturZielInProjekt = Path.Combine(projektOrdnerPfad, zielTexturName);
            File.Copy(texturHauptPfad, texturZielInProjekt, true);
            AssetDatabase.ImportAsset("Assets/" + unityZielOrdner + "/" + zielTexturName);
        }

        // 2. Kopiere das 3D-Modell
        string modellZielInProjekt = Path.Combine(projektOrdnerPfad, zielModellName);
        try
        {
            File.Copy(modellHauptPfad, modellZielInProjekt, true);
            string relativeAssetPath = "Assets/" + unityZielOrdner + "/" + zielModellName;
            AssetDatabase.ImportAsset(relativeAssetPath);
            
            Debug.Log($"[Editor] FBX und Textur erfolgreich in '{unityZielOrdner}' hochgeladen.");
        }
        catch (Exception e)
        {
            Debug.LogError($"[Editor] Fehler beim Kopieren: {e.Message}");
        }
    }

    private void LadeModellAusProjekt()
    {
        string relativeAssetPath = "Assets/" + unityZielOrdner + "/" + zielModellName;
        GameObject fbxPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(relativeAssetPath);

        if (fbxPrefab != null)
        {
            // Alten Inhalt löschen
            if (instanziiertesModell != null)
            {
                Destroy(instanziiertesModell);
            }
            else if (transform.childCount > 0)
            {
                for (int i = transform.childCount - 1; i >= 0; i--)
                {
                    Destroy(transform.GetChild(i).gameObject);
                }
            }

            // Neues Modell erstellen
            instanziiertesModell = Instantiate(fbxPrefab, transform);
            instanziiertesModell.transform.localPosition = Vector3.zero;
            instanziiertesModell.transform.localRotation = Quaternion.identity;

            Debug.Log($"[Editor] Modell '{zielModellName}' inklusive Textur erfolgreich geladen!");
        }
        else
        {
            Debug.LogError($"[Editor] Konnte das FBX-Asset unter '{relativeAssetPath}' nicht laden.");
        }
    }
#endif
}