using System;
using System.IO;
using System.Linq;
using UnityEngine;

#if UNITY_EDITOR
using UnityEditor;
#endif

public class PlayerHeadUpdater : MonoBehaviour
{
    [Header("Ordner mit neuen Modellen")]
    [SerializeField]
    private string sourceFolder = @"C:\temp";

    [Header("Unity-Zielordner")]
    [SerializeField]
    private string targetFolder = "Assets/Resources/Blocks";

    [Header("Modell in der Szene")]
    [SerializeField]
    private Transform modelParent;

    private const string TargetName = "PlayerHead";

    private void Start()
    {
#if UNITY_EDITOR
        UpdatePlayerHead();
#else
        Debug.LogWarning(
            "Der FBX-Import funktioniert über dieses Skript " +
            "nur im Unity Editor.", this);
#endif
    }

#if UNITY_EDITOR
    private void UpdatePlayerHead()
    {
        try
        {
            if (!Directory.Exists(sourceFolder))
            {
                Debug.LogError("Quellordner nicht gefunden: " + sourceFolder);
                return;
            }

            Directory.CreateDirectory(targetFolder);

            // Neue FBX-Datei suchen, PlayerHead.fbx ignorieren.
            string newFbx = Directory.GetFiles(sourceFolder, "*.fbx")
                .FirstOrDefault(path =>
                    !Path.GetFileName(path).Equals(
                        TargetName + ".fbx",
                        StringComparison.OrdinalIgnoreCase));

            if (newFbx == null)
            {
                Debug.Log("Keine neue FBX-Datei gefunden.");
                return;
            }

            // Passende PNG anhand des ursprünglichen Dateinamens suchen.
            string originalName = Path.GetFileNameWithoutExtension(newFbx);
            string matchingPng = Directory.GetFiles(sourceFolder, "*.png")
                .FirstOrDefault(path =>
                    Path.GetFileNameWithoutExtension(path).Equals(
                        originalName,
                        StringComparison.OrdinalIgnoreCase));

            if (matchingPng == null)
            {
                Debug.LogError(
                    "Keine passende PNG-Datei für " +
                    Path.GetFileName(newFbx) + " gefunden.");
                return;
            }

            string targetFbx = Path.Combine(
                targetFolder, TargetName + ".fbx");
            string targetPng = Path.Combine(
                targetFolder, TargetName + ".png");

            // Neue Dateien zunächst in temporäre Dateien kopieren.
            string tempFbx = targetFbx + ".tmp";
            string tempPng = targetPng + ".tmp";

            File.Copy(newFbx, tempFbx, true);
            File.Copy(matchingPng, tempPng, true);

            // Alte Dateien im Unity-Zielordner entfernen.
            if (File.Exists(targetFbx))
                File.Delete(targetFbx);

            if (File.Exists(targetPng))
                File.Delete(targetPng);

            // Neue Dateien unter den festen Namen ablegen.
            File.Move(tempFbx, targetFbx);
            File.Move(tempPng, targetPng);

            // Die verarbeiteten Quelldateien entfernen.
            File.Delete(newFbx);
            File.Delete(matchingPng);

            // Unity-Import aktualisieren.
            AssetDatabase.Refresh(
                ImportAssetOptions.ForceSynchronousImport);

            AssetDatabase.ImportAsset(
                targetFbx, ImportAssetOptions.ForceUpdate);

            AssetDatabase.ImportAsset(
                targetPng, ImportAssetOptions.ForceUpdate);

            GameObject model =
                AssetDatabase.LoadAssetAtPath<GameObject>(targetFbx);

            if (model == null)
            {
                Debug.LogError("Das neue Modell konnte nicht geladen werden.");
                return;
            }

            Transform parent = modelParent != null
                ? modelParent
                : transform;

            // Bisheriges Modell im Container entfernen.
            for (int i = parent.childCount - 1; i >= 0; i--)
                Destroy(parent.GetChild(i).gameObject);

            // Neues Modell erzeugen.
            GameObject instance = Instantiate(model, parent);
            instance.name = TargetName;
            instance.transform.localPosition = Vector3.zero;
            instance.transform.localRotation = Quaternion.identity;
            instance.transform.localScale = Vector3.one;

            Debug.Log(
                "PlayerHead wurde ersetzt und neu geladen. " +
                "Verarbeitete Dateien: " + originalName);
        }
        catch (Exception ex)
        {
            Debug.LogError("Fehler beim Ersetzen von PlayerHead: " + ex);
        }
    }
#endif
}