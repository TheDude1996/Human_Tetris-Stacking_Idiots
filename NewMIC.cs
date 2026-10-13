using UnityEngine;
using System;
using System.IO;



public class KinectMicRecorder : MonoBehaviour
{

    void Start()
    {
        Debug.Log("Verfügbare Mikrofone:");
        foreach (string d in Microphone.devices)
            Debug.Log("  - " + d);
    }

    private AudioClip _clip;
    private bool _recording = false;
    private float _startTime;
    private const float Duration = 3f;

    private string _deviceName = "Mikrofonarray (Microsoft Kinect USB Audio)";

    void OnGUI()
    {
        if (!_recording)
        {
            if (GUI.Button(new Rect(10, 10, 120, 40), "Record 3s"))
            {
                _clip = Microphone.Start(_deviceName, true, (int)Duration, 16000);
                if (_clip == null)
                {
                    Debug.LogError($"Device '{_deviceName}' not found. " +
                        $"Available: {string.Join(", ", Microphone.devices)}");
                }
                else
                {
                    _recording = true;
                    _startTime = Time.time;
                }
            }
        }
        else
        {
            GUI.Label(new Rect(10, 10, 200, 40), "Recording...");
            if (Time.time - _startTime >= Duration)
            {
                Microphone.End(_deviceName);
                _recording = false;
                string saveDir = Application.isEditor
                    ? Application.streamingAssetsPath
                    : Application.persistentDataPath;
                SaveWav(_clip, Path.Combine(saveDir, "kinect_sample.wav"));
                Debug.Log("Saved!");
            }
        }
    }

    void SaveWav(AudioClip clip, string path)
    {
        // GetData erwartet float[] — Werte im Bereich -1.0f bis 1.0f
        int totalSamples = clip.samples * clip.channels;
        float[] floatData = new float[totalSamples];
        clip.GetData(floatData, 0);

        // Float → 16-bit Int konvertieren
        short[] intData = new short[totalSamples];
        for (int i = 0; i < totalSamples; i++)
        {
            intData[i] = (short)(floatData[i] * 32767f);
        }

        byte[] byteData = new byte[intData.Length * 2];
        Buffer.BlockCopy(intData, 0, byteData, 0, byteData.Length);

        int dataLen = byteData.Length;
        int sr = clip.frequency;
        int ch = clip.channels;
        int byteRate = sr * ch * 2;
        int blockAlign = ch * 2;

        using (var fs = new FileStream(path, FileMode.Create))
        using (var w = new BinaryWriter(fs))
        {
            w.Write(new byte[] { (byte)'R', (byte)'I', (byte)'F', (byte)'F' });
            w.Write(36 + dataLen);
            w.Write(new byte[] { (byte)'W', (byte)'A', (byte)'V', (byte)'E' });
            w.Write(new byte[] { (byte)'f', (byte)'m', (byte)'t', (byte)' ' });
            w.Write(16);
            w.Write((short)1);
            w.Write((short)ch);
            w.Write(sr);
            w.Write(byteRate);
            w.Write((short)blockAlign);
            w.Write((short)16);
            w.Write(new byte[] { (byte)'d', (byte)'a', (byte)'t', (byte)'a' });
            w.Write(dataLen);
            w.Write(byteData);
        }
    }
}
