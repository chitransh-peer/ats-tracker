"use client";

import { AppShell, StatCard } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { funnelData, hiringTrend, scoreDistribution, sourcePerformance } from "@/lib/mock-data";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const colors = ["#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#a855f7"];

export function ReportsClient() {
  return (
    <AppShell
      title="Reports & Analytics"
      breadcrumbs={[{ label: "Home", to: "/" }, { label: "Reports" }]}
      actions={
        <>
          <Button variant="outline" size="sm">
            Export
          </Button>
          <Button size="sm">Saved views</Button>
        </>
      }
    >
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <StatCard label="Open positions" value={48} />
        <StatCard label="Time to fill" value="32d" change="-4d" tone="success" />
        <StatCard label="Offer acceptance" value="87%" tone="success" />
        <StatCard label="Cost per hire" value="$3,240" />
        <StatCard label="Aging jobs (60d+)" value={7} tone="warning" />
      </div>

      <Tabs defaultValue="funnel">
        <TabsList>
          <TabsTrigger value="funnel">Funnel</TabsTrigger>
          <TabsTrigger value="trend">Trend</TabsTrigger>
          <TabsTrigger value="source">Source</TabsTrigger>
          <TabsTrigger value="ai">AI scores</TabsTrigger>
          <TabsTrigger value="recruiter">Recruiter</TabsTrigger>
        </TabsList>

        <TabsContent value="funnel" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Hiring funnel</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={340}>
                <BarChart data={funnelData} layout="vertical" margin={{ left: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" className="text-xs" />
                  <YAxis type="category" dataKey="stage" className="text-xs" width={90} />
                  <Tooltip />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]} fill="#4f46e5" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="trend" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Hiring trend — offers vs hires</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={340}>
                <LineChart data={hiringTrend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="offers" stroke="#4f46e5" strokeWidth={2} />
                  <Line type="monotone" dataKey="hires" stroke="#10b981" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="source" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Source effectiveness</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={340}>
                <PieChart>
                  <Pie
                    data={sourcePerformance}
                    dataKey="value"
                    nameKey="source"
                    innerRadius={80}
                    outerRadius={130}
                  >
                    {sourcePerformance.map((_, i) => (
                      <Cell key={i} fill={colors[i % colors.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ai" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">AI match score distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={340}>
                <BarChart data={scoreDistribution}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="bucket" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]} fill="#a855f7" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="recruiter" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recruiter productivity</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="p-3 text-left">Recruiter</th>
                    <th className="p-3 text-right">Open jobs</th>
                    <th className="p-3 text-right">Screens</th>
                    <th className="p-3 text-right">Interviews</th>
                    <th className="p-3 text-right">Offers</th>
                    <th className="p-3 text-right">Hires</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {[
                    ["Priya Sharma", 12, 42, 18, 4, 3],
                    ["Marcus Chen", 9, 38, 15, 3, 2],
                    ["Elena Rodriguez", 11, 50, 22, 5, 4],
                    ["Aditya Nair", 7, 28, 12, 2, 2],
                    ["Sarah Kim", 10, 44, 20, 4, 3],
                  ].map((row) => (
                    <tr key={row[0] as string} className="hover:bg-muted/30">
                      {row.map((v, i) => (
                        <td key={i} className={i === 0 ? "p-3" : "p-3 text-right"}>
                          {v}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}
