using System.Collections;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Nimmt ein 2-Sekunden-Sample vom Spieler auf, extrahiert daraus automatisch
/// den lautesten kurzen Ausschnitt ("Grain") und spielt damit die Tetris-Melodie
/// als endlos loopenden Hintergrund-Track ab. Jede Note transponiert den
/// gleichen Grain per Pitch-Shift (AudioSource.pitch) auf die Zielhöhe.
///
/// Setup in der Szene:
/// 1. Leeres GameObject "MelodyPlayer" erstellen
/// 2. Dieses Skript daran hängen
/// 3. Recording per StartCoroutine(RecordAndPlay()) starten, z.B. am Levelstart
/// </summary>
public class TetrisMelodyPlayer : MonoBehaviour
{
    [Header("Aufnahme-Einstellungen")]
    [SerializeField] private int recordSeconds = 2;
    [SerializeField] private int sampleRate = 44100;
    [SerializeField] private float grainLengthSeconds = 0.3f;

    [Header("Wiedergabe-Einstellungen")]
    [SerializeField] private float bpm = MelodyData.DefaultBpm;
    [SerializeField] private int voicePoolSize = 4;
    [SerializeField] private bool loopMelody = true;

    private AudioClip _baseGrain;
    private List<AudioSource> _voicePool = new List<AudioSource>();
    private int _nextVoiceIndex = 0;
    private Coroutine _playbackRoutine;

    /// <summary>
    /// Startet Mikrofonaufnahme, extrahiert den Grain und beginnt danach
    /// automatisch die Melodie-Wiedergabe.
    /// </summary>
    public IEnumerator RecordAndPlay()
    {
        yield return StartCoroutine(RecordSample());

        if (_baseGrain == null)
        {
            Debug.LogWarning("Kein Grain extrahiert - Aufnahme fehlgeschlagen oder zu leise.");
            yield break;
        }

        SetupVoicePool();
        StopPlayback();
        _playbackRoutine = StartCoroutine(PlayMelodyLoop());
    }

    // ---------------------------------------------------------------
    // 1) Aufnahme + Grain-Extraktion
    // ---------------------------------------------------------------

    private IEnumerator RecordSample()
    {
        if (Microphone.devices.Length == 0)
        {
            Debug.LogWarning("Kein Mikrofon gefunden.");
            yield break;
        }

        string device = Microphone.devices[0];
        AudioClip rawClip = Microphone.Start(device, false, recordSeconds, sampleRate);

        // Warten bis Unity tatsächlich Samples liefert
        while (Microphone.GetPosition(device) <= 0) yield return null;

        yield return new WaitForSeconds(recordSeconds);
        Microphone.End(device);

        _baseGrain = ExtractLoudestGrain(rawClip, grainLengthSeconds);
    }

    /// <summary>
    /// Durchsucht die Aufnahme mit einem gleitenden Fenster nach dem
    /// Abschnitt mit der höchsten RMS-Energie (= "lautester" Moment)
    /// und schneidet genau diesen als neuen, kurzen AudioClip heraus.
    /// </summary>
    private AudioClip ExtractLoudestGrain(AudioClip source, float grainSeconds)
    {
        int channels = source.channels;
        int totalSamples = source.samples * channels;
        float[] allData = new float[totalSamples];
        source.GetData(allData, 0);

        int grainSamples = Mathf.Min(Mathf.RoundToInt(grainSeconds * source.frequency) * channels, totalSamples);
        if (grainSamples <= 0) return null;

        int hop = Mathf.Max(grainSamples / 4, channels); // 75% Überlappung beim Durchsuchen

        int bestStart = 0;
        float bestRms = -1f;

        for (int start = 0; start + grainSamples <= totalSamples; start += hop)
        {
            float sumSquares = 0f;
            for (int i = start; i < start + grainSamples; i++)
                sumSquares += allData[i] * allData[i];

            float rms = Mathf.Sqrt(sumSquares / grainSamples);
            if (rms > bestRms)
            {
                bestRms = rms;
                bestStart = start;
            }
        }

        if (bestRms <= 0.0001f)
        {
            Debug.LogWarning("Aufnahme scheint (fast) stumm zu sein.");
        }

        float[] grainData = new float[grainSamples];
        System.Array.Copy(allData, bestStart, grainData, 0, grainSamples);

        AudioClip grain = AudioClip.Create("PlayerGrain", grainSamples / channels, channels, source.frequency, false);
        grain.SetData(grainData, 0);
        return grain;
    }

    // ---------------------------------------------------------------
    // 2) Wiedergabe / Sequenzer
    // ---------------------------------------------------------------

    private void SetupVoicePool()
    {
        foreach (var src in _voicePool)
            if (src != null) Destroy(src.gameObject);
        _voicePool.Clear();

        for (int i = 0; i < voicePoolSize; i++)
        {
            var go = new GameObject($"Voice_{i}");
            go.transform.SetParent(transform);
            var src = go.AddComponent<AudioSource>();
            src.clip = _baseGrain;
            src.playOnAwake = false;
            _voicePool.Add(src);
        }
    }

    private AudioSource GetNextVoice()
    {
        var src = _voicePool[_nextVoiceIndex];
        _nextVoiceIndex = (_nextVoiceIndex + 1) % _voicePool.Count;
        return src;
    }

    private IEnumerator PlayMelodyLoop()
    {
        float secondsPerBeat = 60f / bpm;

        do
        {
            double scheduleTime = AudioSettings.dspTime + 0.1; // kleiner Puffer für sauberes Scheduling

            foreach (var note in MelodyData.MainPhrase)
            {
                float noteDuration = note.durationBeats * secondsPerBeat;

                if (note.midiNote > 0)
                {
                    var voice = GetNextVoice();
                    voice.pitch = MidiToPitchRatio(note.midiNote);
                    voice.PlayScheduled(scheduleTime);
                }
                // midiNote == 0 -> Pause, es wird nichts abgespielt

                scheduleTime += noteDuration;
            }

            // Warten bis die Phrase durchgelaufen ist, bevor sie ggf. erneut startet
            double waitUntil = scheduleTime - AudioSettings.dspTime;
            yield return new WaitForSeconds((float)waitUntil);

        } while (loopMelody);
    }

    private float MidiToPitchRatio(int targetMidiNote)
    {
        return Mathf.Pow(2f, (targetMidiNote - MelodyData.BaseMidiNote) / 12f);
    }

    public void StopPlayback()
    {
        if (_playbackRoutine != null)
        {
            StopCoroutine(_playbackRoutine);
            _playbackRoutine = null;
        }
        foreach (var src in _voicePool)
            if (src != null) src.Stop();
    }
}
