'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function SystemPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">System Status</h1>
        <p className="text-muted-foreground mt-2">
          Monitor the health of backend services and MCP servers
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>FastAPI Backend</CardTitle>
              <Badge variant="outline">Checking...</Badge>
            </div>
            <CardDescription>
              Main API server status
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">URL:</span>
                <span className="font-mono">http://localhost:8080</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status:</span>
                <span>Pending check</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Market Data MCP</CardTitle>
              <Badge variant="outline">Checking...</Badge>
            </div>
            <CardDescription>
              Market data service
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">URL:</span>
                <span className="font-mono">http://localhost:8000</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status:</span>
                <span>Pending check</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>News Search MCP</CardTitle>
              <Badge variant="outline">Checking...</Badge>
            </div>
            <CardDescription>
              News search service
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">URL:</span>
                <span className="font-mono">http://localhost:8001</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status:</span>
                <span>Pending check</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Agent System</CardTitle>
            <CardDescription>
              Multi-agent orchestration
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Quant Agent:</span>
                <Badge variant="secondary">Ready</Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">News Agent:</span>
                <Badge variant="secondary">Ready</Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Social Agent:</span>
                <Badge variant="secondary">Ready</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <p className="text-sm text-muted-foreground text-center py-4">
        Real-time status checks will be implemented via API
      </p>
    </div>
  );
}
