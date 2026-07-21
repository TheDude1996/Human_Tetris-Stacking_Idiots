using System.Collections.Generic;

/// <summary>
/// Notendaten der Tetris-Melodie ("Korobeiniki", gemeinfreie russische Volksweise,
/// bekannt aus dem Original-Game-Boy-Tetris-Theme).
/// Jede Note besteht aus einer MIDI-Notennummer und einer Dauer in Beats.
/// MIDI-Notennummer 0 = Pause.
/// </summary>
public static class MelodyData
{
    public struct Note
    {
        public int midiNote;      // 0 = Pause, sonst MIDI-Nummer (z.B. 76 = E5)
        public float durationBeats;

        public Note(int midiNote, float durationBeats)
        {
            this.midiNote = midiNote;
            this.durationBeats = durationBeats;
        }
    }

    // Tempo der Melodie in BPM (klassisch recht flott, ~150-160 BPM)
    public const float DefaultBpm = 150f;

    // Referenz-Note, auf die sich der Pitch-Shift-Faktor bezieht.
    // (Die tatsächliche Tonhöhe der Aufnahme ist beliebig - alle Noten
    // werden relativ dazu hoch/runter transponiert.)
    public const int BaseMidiNote = 60; // Middle C

    // Erste Phrase des Tetris-Themes (E-Moll), Dauer in Achtelnoten-Einheiten (0.5 Beat = 1 Achtel)
    public static readonly List<Note> MainPhrase = new List<Note>
    {
        new Note(76, 1f),   // E5
        new Note(71, 0.5f), // B4
        new Note(72, 0.5f), // C5
        new Note(74, 1f),   // D5
        new Note(72, 0.5f), // C5
        new Note(71, 0.5f), // B4
        new Note(69, 1f),   // A4
        new Note(69, 0.5f), // A4
        new Note(72, 0.5f), // C5
        new Note(76, 1f),   // E5
        new Note(74, 0.5f), // D5
        new Note(72, 0.5f), // C5
        new Note(71, 1.5f), // B4
        new Note(72, 0.5f), // C5
        new Note(74, 1f),   // D5
        new Note(76, 1f),   // E5
        new Note(72, 1f),   // C5
        new Note(69, 1f),   // A4
        new Note(69, 1f),   // A4
        new Note(0, 1f),    // Pause
    };
}
