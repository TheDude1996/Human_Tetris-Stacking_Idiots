using System;
using System.IO;
using UnityEngine;

#if UNITY_EDITOR
using UnityEditor;
#endif

public class PlayerHeadUpdater : MonoBehaviour
{
    [SerializeField] private string sourceFolder = @"C:\temp";
    [SerializeField] private string targetFolder = "Assets/Resources/Blocks";
    [SerializeField] private Transform modelParent;

#if UNITY_EDITOR
    private FileSystemWatcher watcher;
    private bool updateNeeded;
    private DateTime lastChange;
#endif

    private void Start()
    {
#if UNITY_EDITOR
        watcher = new FileSystemWatcher(sourceFolder);
        watcher.Filter = "*.*";
        watcher.NotifyFilter = NotifyFilters.LastWrite |
                               NotifyFilters.FileName |
                               NotifyFilters.Size;

        watcher.Changed += OnFileChanged;
        watcher.Created += OnFileChanged;
        watcher.Renamed += OnFileChanged;
        watcher.EnableRaisingEvents = true;

        UpdateModel();
#endif
    }

#if UNITY_EDITOR
    private void OnFileChanged(object sender, FileSystemEventArgs e)
    {
        if (e.FullPath.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase) ||
            e.FullPath.EndsWith(".png", StringComparison.OrdinalIgnoreCase))
        {
            updateNeeded = true;
            lastChange = DateTime.UtcNow;
        }
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

            File.Copy(fbx, targetFbx, true);
            File.Copy(png, targetPng, true);

            AssetDatabase.Refresh();

            GameObject model =
                AssetDatabase.LoadAssetAtPath<GameObject>(targetFbx);

            if (model == null)
                return;

            Transform parent = modelParent != null ? modelParent : transform;

            for (int i = parent.childCount - 1; i >= 0; i--)
            {
                if (parent.GetChild(i).name == "PlayerHead")
                    DestroyImmediate(parent.GetChild(i).gameObject);
            }

            GameObject instance = Instantiate(model, parent);
            instance.name = "PlayerHead";
            instance.transform.localPosition = Vector3.zero;
            instance.transform.localRotation = Quaternion.identity;
            instance.transform.localScale = Vector3.one;

            updateNeeded = false;
            Debug.Log("PlayerHead wurde aktualisiert.");
        }
        catch (IOException)
        {
            // Datei wird noch geschrieben; später erneut versuchen.
        }
    }

    private string FindNewest(string extension)
    {
        string newest = null;
        DateTime newestTime = DateTime.MinValue;

        foreach (string file in Directory.GetFiles(sourceFolder, "*" + extension))
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
            watcher.Dispose();
    }
#endif
}