import React from "react";
import { Database, Satellite, Map, ShieldAlert } from "lucide-react";

export default function DataSources() {
  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Data Sources & Provenance</h2>
        <p className="text-slate-400">OceanGuard relies on fused satellite and geospatial data to detect dark vessels.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* SAR */}
        <div className="bg-ocean-800 border border-ocean-700 p-6 rounded-lg">
          <div className="w-10 h-10 bg-teal-500/20 text-teal-400 rounded-lg flex items-center justify-center mb-4">
            <Satellite className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Synthetic Aperture Radar (SAR)</h3>
          <p className="text-sm text-slate-300 mb-4 leading-relaxed">
            SAR satellites beam microwaves to the Earth's surface and measure the reflection. 
            Because metal vessels are highly reflective, they appear as bright pixels on the ocean surface, 
            even through clouds and at night.
          </p>
          <div className="text-xs text-slate-500">Sources: Sentinel-1, xView3 Dataset</div>
        </div>

        {/* AIS */}
        <div className="bg-ocean-800 border border-ocean-700 p-6 rounded-lg">
          <div className="w-10 h-10 bg-teal-500/20 text-teal-400 rounded-lg flex items-center justify-center mb-4">
            <Database className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Automatic Identification System (AIS)</h3>
          <p className="text-sm text-slate-300 mb-4 leading-relaxed">
            AIS is a tracking system that ships use to broadcast their location to avoid collisions. 
            OceanGuard correlates SAR detections with AIS data. If a SAR detection lacks a matching AIS signal, 
            the vessel is flagged as "Dark".
          </p>
          <div className="text-xs text-slate-500">Sources: Global Fishing Watch</div>
        </div>

        {/* MPAs */}
        <div className="bg-ocean-800 border border-ocean-700 p-6 rounded-lg">
          <div className="w-10 h-10 bg-teal-500/20 text-teal-400 rounded-lg flex items-center justify-center mb-4">
            <Map className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Marine Protected Areas (MPAs)</h3>
          <p className="text-sm text-slate-300 mb-4 leading-relaxed">
            Geospatial boundaries of protected marine zones. Detections inside or within 5km of these 
            boundaries are assigned significantly higher risk scores.
          </p>
          <div className="text-xs text-slate-500">Sources: ProtectedPlanet (WDPA), IUCN</div>
        </div>

        {/* Infrastructure */}
        <div className="bg-ocean-800 border border-ocean-700 p-6 rounded-lg">
          <div className="w-10 h-10 bg-teal-500/20 text-teal-400 rounded-lg flex items-center justify-center mb-4">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Coastal Infrastructure</h3>
          <p className="text-sm text-slate-300 mb-4 leading-relaxed">
            Locations of ports, marinas, and oil platforms. Used to help contextualise 
            vessel behavior (e.g. vessels loitering near ports may just be waiting for entry).
          </p>
          <div className="text-xs text-slate-500">Sources: OpenStreetMap (Overpass API)</div>
        </div>

      </div>
    </div>
  );
}
