using System;
using System.IO;
using UnityEngine;

#if UNITY_EDITOR
using UnityEditor; // Wird benötigt, um die FBX direkt in das Unity-Projekt einzubinden
#endif

public class ModelManager2023 : MonoBehaviour
{
    [Header("Einstellungen (Externer Ordner)")]
    [SerializeField] private string ordnerName = "SpielerTexturen"; // Name des Ordners in Dokumente
    [SerializeField] private string zielDateiName = "PlayerHead.fbx";

    [Header("Einstellungen (Unity Projektordner)")]
    [Tooltip("Der Ordner innerhalb von Assets, in den die FBX kopiert werden soll")]
    [SerializeField] private string unityZielOrdner = "ImportedModels";

    private string ordnerPfad;
    private string hauptDateiPfad;
    private GameObject instanziiertesModell;

    void Start()
    {
        // Generiert den Pfad im Dokumente-Ordner des PCs
        ordnerPfad = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), ordnerName);
        hauptDateiPfad = Path.Combine(ordnerPfad, zielDateiName);

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
            if (extension == ".fbx")
            {
                RotiereAlteDateien();
                
                // Verschiebe und benenne die neue FBX im externen Ordner um
                File.Move(datei, hauptDateiPfad);
                Debug.Log($"Neue FBX-Datei erkannt und als '{zielDateiName}' gesetzt.");
                break; 
            }
        }

        // Wenn die Datei existiert, binden wir sie ins Projekt ein und laden sie
        if (File.Exists(hauptDateiPfad))
        {
#if UNITY_EDITOR
            KopiereInUnityProjekt(hauptDateiPfad);
            LadeModellAusProjekt();
#endif
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
            backupPfad = Path.Combine(ordnerPfad, $"PlayerHead_{index}.fbx");
            index++;
        } 
        while (File.Exists(backupPfad));

        File.Move(hauptDateiPfad, backupPfad);
        Debug.Log($"Alte FBX archiviert als: {Path.GetFileName(backupPfad)}");
    }

#if UNITY_EDITOR
    private void KopiereInUnityProjekt(string quellPfad)
    {
        // Pfad innerhalb des Unity-Projekts aufbauen (z.B. Assets/ImportedModels)
        string projektOrdnerPfad = Path.Combine(Application.dataPath, unityZielOrdner);
        
        // Erstelle den Ordner im Unity-Projekt, falls er noch nicht existiert
        if (!Directory.Exists(projektOrdnerPfad))
        {
            Directory.CreateDirectory(projektOrdnerPfad);
        }

        // Ziel-Dateipfad im Unity-Projekt (z.B. Assets/ImportedModels/PlayerHead.fbx)
        string dateiZielPfadInProjekt = Path.Combine(projektOrdnerPfad, zielDateiName);

        try
        {
            // Datei kopieren (true = überschreiben, falls sie schon existiert)
            File.Copy(quellPfad, dateiZielPfadInProjekt, true);

            // Unity Bescheid geben, damit das Asset im Project-Window registriert wird
            string relativeAssetPath = "Assets/" + unityZielOrdner + "/" + zielDateiName;
            AssetDatabase.ImportAsset(relativeAssetPath);
            
            Debug.Log($"[Editor] FBX-Datei erfolgreich in das Unity-Projekt hochgeladen: {relativeAssetPath}");
        }
        catch (Exception e)
        {
            Debug.LogError($"[Editor] Fehler beim Kopieren der FBX in das Unity-Projekt: {e.Message}");
        }
    }

    private void LadeModellAusProjekt()
    {
        // Pfad zum Asset im Projekt fenster
        string relativeAssetPath = "Assets/" + unityZielOrdner + "/" + zielDateiName;

        // Lädt die FBX-Datei als GameObject-Prefab aus dem Projekt ordner
        GameObject fbxPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(relativeAssetPath);

        if (fbxPrefab != null)
        {
            // Falls bereits ein Modell geladen war, zerstören wir es zuerst
            if (instanziiertesModell != null)
            {
                Destroy(instanziiertesModell);
            }
            // Falls das Skript auf einem Objekt liegt, das bereits alte Kinder hat, machen wir sauber
            else if (transform.childCount > 0)
            {
                for (int i = transform.childCount - 1; i >= 0; i--)
                {
                    Destroy(transform.GetChild(i).gameObject);
                }
            }

            // Bringt das neue 3D-Modell ins Spiel und macht es zum Kind dieses Objekts
            instanziiertesModell = Instantiate(fbxPrefab, transform);
            
            // Setzt die lokale Position und Rotation zurück, damit es perfekt mittig sitzt
            instanziiertesModell.transform.localPosition = Vector3.zero;
            instanziiertesModell.transform.localRotation = Quaternion.identity;

            Debug.Log($"[Editor] 3D-Modell '{zielDateiName}' erfolgreich im Spiel platziert.");
        }
        else
        {
            Debug.LogError($"[Editor] Konnte das FBX-Asset unter '{relativeAssetPath}' nicht laden.");
        }
    }
#endif
}
