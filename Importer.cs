using System;
using System.IO;
using UnityEngine;

#if UNITY_EDITOR
using UnityEditor;
#endif

public class PlayerHeadUpdater : MonoBehaviour
{
    [Header("Quellordner")]
    [SerializeField] private string sourceFolder = @"C:\temp";

    [Header("Unity-Zielordner")]
    [SerializeField] private string targetFolder = "Assets/Resources/Blocks";

    [Header("Modell in der Szene")]
    [SerializeField] private Transform modelParent;

#if UNITY_EDITOR
    private FileSystemWatcher watcher;
    private bool updateNeeded;
    private DateTime lastChange;
#endif

    private void Start()
    {
#if UNITY_EDITOR
        if (!Directory.Exists(sourceFolder))
            Directory.CreateDirectory(sourceFolder);

        watcher = new FileSystemWatcher(sourceFolder)
        {
            Filter = "*.*",
            NotifyFilter = NotifyFilters.LastWrite |
                           NotifyFilters.FileName |
                           NotifyFilters.Size,
            EnableRaisingEvents = false
        };

        watcher.Changed += OnFileChanged;
        watcher.Created += OnFileChanged;
        watcher.Renamed += OnFileRenamed;
        watcher.EnableRaisingEvents = true;

        UpdateModel();
#endif
    }

#if UNITY_EDITOR
    private void OnFileChanged(object sender, FileSystemEventArgs e)
    {
        if (IsRelevantFile(e.FullPath))
        {
            updateNeeded = true;
            lastChange = DateTime.UtcNow;
        }
    }

    private void OnFileRenamed(object sender, RenamedEventArgs e)
    {
        OnFileChanged(sender, e);
    }

    private bool IsRelevantFile(string path)
    {
        return path.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase) ||
               path.EndsWith(".png", StringComparison.OrdinalIgnoreCase);
    }

    private void Update()
    {
        if (updateNeeded &&
            (DateTime.UtcNow - lastChange).TotalSeconds > 2)
        {
            UpdateModel();
        }
    }

    private void UpdateModel()
    {
        try
        {
            string fbx = FindNewest(".fbx");
            string png = FindNewest(".png");

            if (fbx == null || png == null)
                return;

            Directory.CreateDirectory(targetFolder);

            string targetFbx = targetFolder + "/PlayerHead.fbx";
            string targetPng = targetFolder + "/PlayerHead.png";

            // Dateien ersetzen
            File.Copy(fbx, targetFbx, true);
            File.Copy(png, targetPng, true);

            // Unity-Assets neu importieren
            AssetDatabase.Refresh(
                ImportAssetOptions.ForceSynchronousImport);

            AssetDatabase.ImportAsset(
                targetFbx, ImportAssetOptions.ForceUpdate);

            AssetDatabase.ImportAsset(
                targetPng, ImportAssetOptions.ForceUpdate);

            // Modell und Textur laden
            GameObject model =
                AssetDatabase.LoadAssetAtPath<GameObject>(targetFbx);

            Texture2D texture =
                AssetDatabase.LoadAssetAtPath<Texture2D>(targetPng);

            if (model == null)
            {
                Debug.LogError("PlayerHead.fbx konnte nicht geladen werden.");
                return;
            }

            if (texture == null)
            {
                Debug.LogError("PlayerHead.png konnte nicht geladen werden.");
                return;
            }

            Transform parent = modelParent != null
                ? modelParent
                : transform;

            // Altes PlayerHead-Modell entfernen
            for (int i = parent.childCount - 1; i >= 0; i--)
            {
                Transform child = parent.GetChild(i);

                if (child.name == "PlayerHead")
                    DestroyImmediate(child.gameObject);
            }

            // Neues Modell erstellen
            GameObject instance = Instantiate(model, parent);
            instance.name = "PlayerHead";

            instance.transform.localPosition = Vector3.zero;
            instance.transform.localRotation = Quaternion.identity;
            instance.transform.localScale = Vector3.one;

            // Textur allen Materialien zuweisen
            foreach (Renderer renderer in
                     instance.GetComponentsInChildren<Renderer>())
            {
                foreach (Material material in renderer.materials)
                {
                    if (material.HasProperty("_BaseMap"))
                        material.SetTexture("_BaseMap", texture);

                    if (material.HasProperty("_MainTex"))
                        material.SetTexture("_MainTex", texture);
                }
            }

            updateNeeded = false;

            Debug.Log("PlayerHead wurde mit Textur aktualisiert.");
        }
        catch (IOException)
        {
            // Datei ist noch in Benutzung.
            // Erneuter Versuch beim nächsten Datei-Ereignis.
            updateNeeded = true;
            lastChange = DateTime.UtcNow;
        }
        catch (Exception ex)
        {
            Debug.LogError("Fehler beim Aktualisieren: " + ex);
        }
    }

    private string FindNewest(string extension)
    {
        string newest = null;
        DateTime newestTime = DateTime.MinValue;

        foreach (string file in Directory.GetFiles(
                     sourceFolder, "*" + extension))
        {
            DateTime time = File.GetLastWriteTimeUtc(file);

            if (time > newestTime)
            {
                newestTime = time;
                newest = file;
            }
        }

        return newest;
    }

    private void OnDestroy()
    {
        if (watcher != null)
        {
            watcher.EnableRaisingEvents = false;
            watcher.Dispose();
            watcher = null;
        }
    }
#endif
}