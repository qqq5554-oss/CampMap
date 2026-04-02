import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import type { Campsite } from "../../types/campsite";

interface Props {
  campsites: Campsite[];
}

export default function CampMap({ campsites }: Props) {
  const points = campsites.filter((c) => c.lat != null && c.lng != null);

  return (
    <MapContainer
      center={[23.8, 121.0]}
      zoom={8}
      className="h-[400px] w-full rounded-xl z-0"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {points.map((camp) => (
        <Marker key={camp.id} position={[camp.lat!, camp.lng!]}>
          <Popup>
            <strong>{camp.name}</strong>
            <br />
            {camp.address || `${camp.city}${camp.district}`}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
