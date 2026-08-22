using System;
using UnityEngine;

namespace BerlinWorld.Geo
{
    public static class BerlinCoordinates
    {
        public static Vector3 UtmToUnity(double easting, double altitude, double northing, BerlinWorldSettings settings)
        {
            return new Vector3(
                (float)(easting - settings.WorldOriginEasting),
                (float)altitude,
                (float)(northing - settings.WorldOriginNorthing));
        }

        public static void UnityToUtm(Vector3 unityPosition, BerlinWorldSettings settings, out double easting, out double northing)
        {
            easting = settings.WorldOriginEasting + unityPosition.x;
            northing = settings.WorldOriginNorthing + unityPosition.z;
        }

        public static Vector2Int UnityToTile(Vector3 unityPosition, BerlinWorldSettings settings)
        {
            UnityToUtm(unityPosition, settings, out double easting, out double northing);
            int size = settings.TileSizeMeters;
            return new Vector2Int((int)Math.Floor(easting / size), (int)Math.Floor(northing / size));
        }
    }
}
