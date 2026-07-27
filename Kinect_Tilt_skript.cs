using UnityEngine;
using Microsoft.Kinect;

public class KinectTiltController : MonoBehaviour
{
    [Header("Tasten")]
    public KeyCode tiltUpKey = KeyCode.E;
    public KeyCode tiltDownKey = KeyCode.Q;

    [Header("Einstellungen")]
    public int stepSize = 2;
    public int minTilt = -27;
    public int maxTilt = 27;

    private KinectSensor sensor;
    private int currentTilt;

    private float lastMoveTime;
    public float moveDelay = 0.5f;

    void Start()
    {
        if (KinectSensor.KinectSensors.Count == 0)
        {
            Debug.LogError("Keine Kinect gefunden!");
            return;
        }

        sensor = KinectSensor.KinectSensors[0];

        try
        {
            currentTilt = sensor.ElevationAngle;
            Debug.Log("Aktueller Tilt: " + currentTilt);
        }
        catch
        {
            currentTilt = 0;
        }
    }

    void Update()
    {
        if (sensor == null)
            return;

        if (Time.time - lastMoveTime < moveDelay)
            return;

        if (Input.GetKeyDown(tiltUpKey))
        {
            SetTilt(currentTilt + stepSize);
        }

        if (Input.GetKeyDown(tiltDownKey))
        {
            SetTilt(currentTilt - stepSize);
        }
    }

    private void SetTilt(int angle)
    {
        angle = Mathf.Clamp(angle, minTilt, maxTilt);

        try
        {
            sensor.ElevationAngle = angle;

            currentTilt = angle;
            lastMoveTime = Time.time;

            Debug.Log("Neuer Kinect-Tilt: " + angle + "°");
        }
        catch (System.Exception ex)
        {
            Debug.LogError("Tilt konnte nicht gesetzt werden: " + ex.Message);
        }
    }
}