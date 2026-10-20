using System;
using System.IO;
using UnityEngine;

#if UNITY_EDITOR
using UnityEditor;
#endif

public class PlayerHeadUpdater : MonoBehaviour
{
    [Header("Quelldateien")]
    [SerializeField]
    private string sourceFbxPath = @"C:\temp\PlayerHead.fbx";

    [SerializeField]
    private string sourcePngPath = @"C:\temp\PlayerHead.png";

    [Header("Ziel")]
    [SerializeField]
    private string targetFolder = "Assets/Resources/Blocks";

    [Header("Modell in der Szene")]
    [Tooltip("Leeres GameObject, in dem das Modell erzeugt wird.")]
    [SerializeField]
    private Transform modelParent;

    [SerializeField]
    private string targetModelName = "PlayerHead";

    private void Start()
    {
#if UNITY_EDITOR
        UpdatePlayerModel();
#else
        Debug.LogWarning(
            "PlayerHeadUpdater: Der FBX-Import über AssetDatabase " +
            "funktioniert nur im Unity Editor. In einem Build wird " +
            "das Modell nicht auf diesem Weg aktualisiert.",
            this
        );
#endif
    }

#if UNITY_EDITOR
    private void UpdatePlayerModel()
    {
        try
        {
            // Quelldateien prüfen
            if (!File.Exists(sourceFbxPath))
            {
                Debug.LogError(
                    $"FBX-Datei nicht gefunden: {sourceFbxPath}", this);
                return;
            }

            if (!File.Exists(sourcePngPath))
            {
                Debug.LogError(
                    $"PNG-Datei nicht gefunden: {sourcePngPath}", this);
                return;
            }

            // Zielordner anlegen, falls er nicht existiert
            string absoluteTargetFolder = Path.GetFullPath(targetFolder);

            Directory.CreateDirectory(absoluteTargetFolder);

            string targetFbxPath = Path.Combine(
                targetFolder, targetModelName + ".fbx");

            string targetPngPath = Path.Combine(
                targetFolder, targetModelName + ".png");

            // Vorhandene Dateien überschreiben
            File.Copy(sourceFbxPath, targetFbxPath, true);
            File.Copy(sourcePngPath, targetPngPath, true);

            Debug.Log("FBX und PNG wurden kopiert.");

            // Unity-Assets neu importieren
            AssetDatabase.Refresh(
                ImportAssetOptions.ForceSynchronousImport);

            AssetDatabase.ImportAsset(
                targetFbxPath,
                ImportAssetOptions.ForceUpdate);

            AssetDatabase.ImportAsset(
                targetPngPath,
                ImportAssetOptions.ForceUpdate);

            // Importiertes Modell laden
            GameObject importedModel =
                AssetDatabase.LoadAssetAtPath<GameObject>(
                    targetFbxPath);

            if (importedModel == null)
            {
                Debug.LogError(
                    "Das importierte FBX-Modell konnte nicht geladen werden.",
                    this);
                return;
            }

            // Ziel für das Modell bestimmen
            Transform parent = modelParent != null
                ? modelParent
                : transform;

            // Vorheriges Modell entfernen
            for (int i = parent.childCount - 1; i >= 0; i--)
            {
                GameObject child = parent.GetChild(i).gameObject;

                if (Application.isPlaying)
                    Destroy(child);
                else
                    DestroyImmediate(child);
            }

            // Neues Modell instanziieren
            GameObject newModel = Instantiate(
                importedModel,
                parent);

            newModel.name = targetModelName;

            newModel.transform.localPosition = Vector3.zero;
            newModel.transform.localRotation = Quaternion.identity;
            newModel.transform.localScale = Vector3.one;

            Debug.Log(
                $"Neues Modell '{targetModelName}' wurde geladen.",
                newModel);
        }
        catch (Exception ex)
        {
            Debug.LogError(
                $"Fehler beim Aktualisieren des Player-Modells:\n{ex}",
                this);
        }
    }
#endif
}