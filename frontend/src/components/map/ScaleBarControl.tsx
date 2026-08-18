import { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';

export function ScaleBarControl() {
  const map = useMap();

  useEffect(() => {
    const control = L.control.scale({ metric: true, imperial: false, position: 'bottomleft' });
    control.addTo(map);
    return () => {
      control.remove();
    };
  }, [map]);

  return null;
}
