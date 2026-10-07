"use client";
import { useEffect, useState } from "react";
import { getGraph } from "@/lib/teacherApi";

interface Node { key: string; name: string; order_index: number }
interface Edge { from: string; to: string; strength: string }

export default function GraphPage() {
  const [graph, setGraph] = useState<{ nodes: Node[]; edges: Edge[] } | null>(null);

  useEffect(() => { getGraph().then(setGraph).catch(() => {}); }, []);

  if (!graph) return <div className="text-gray-400">Loading…</div>;

  // Simple layered layout: nodes sorted by order_index, laid out in a grid
  const width = 900;
  const height = 600;
  const cols = 3;
  const nodeW = 180;
  const nodeH = 60;
  const gapX = 40;
  const gapY = 80;

  const nodes = graph.nodes;
  const positions = new Map<string, { x: number; y: number }>();
  nodes.forEach((n, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    positions.set(n.key, {
      x: col * (nodeW + gapX) + 40,
      y: row * (nodeH + gapY) + 40,
    });
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Concept Graph</h1>
        <p className="text-gray-600 text-sm">Arrows point from prerequisite → dependent concept.</p>
      </div>

      <div className="rounded-xl border bg-white overflow-x-auto">
        <svg width={width} height={height} className="block">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5"
              markerWidth="8" markerHeight="8" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#10b981" />
            </marker>
          </defs>

          {graph.edges.map((e, i) => {
            const a = positions.get(e.from);
            const b = positions.get(e.to);
            if (!a || !b) return null;
            // line from center of A to center of B, but trimmed to box edges
            const x1 = a.x + nodeW / 2;
            const y1 = a.y + nodeH;
            const x2 = b.x + nodeW / 2;
            const y2 = b.y;
            return (
              <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
                stroke="#10b981" strokeWidth={1.5} markerEnd="url(#arrow)" opacity={0.6} />
            );
          })}

          {nodes.map((n) => {
            const p = positions.get(n.key)!;
            return (
              <g key={n.key}>
                <rect x={p.x} y={p.y} width={nodeW} height={nodeH} rx={10}
                  fill="#ecfdf5" stroke="#10b981" strokeWidth={1.5} />
                <text x={p.x + nodeW / 2} y={p.y + 24} textAnchor="middle"
                  fontSize="13" fontWeight="600" fill="#065f46">
                  {n.name}
                </text>
                <text x={p.x + nodeW / 2} y={p.y + 44} textAnchor="middle"
                  fontSize="10" fill="#047857" fontFamily="monospace">
                  {n.key}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {nodes.length === 0 && (
        <p className="text-center text-gray-400">No concepts yet — create some first.</p>
      )}
    </div>
  );
}
