import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Analysis Reports</h1>
        <p className="text-muted-foreground mt-2">
          Browse all generated financial analysis reports
        </p>
      </div>

      <div className="space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="hover:bg-accent cursor-pointer transition-colors">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <CardTitle className="flex items-center gap-2">
                    <Skeleton className="h-6 w-16" />
                    <Badge variant="outline">
                      <Skeleton className="h-4 w-20" />
                    </Badge>
                  </CardTitle>
                  <CardDescription>
                    <Skeleton className="h-4 w-48" />
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Quant Score</p>
                  <Skeleton className="h-5 w-12 mt-1" />
                </div>
                <div>
                  <p className="text-muted-foreground">News Sentiment</p>
                  <Skeleton className="h-5 w-16 mt-1" />
                </div>
                <div>
                  <p className="text-muted-foreground">Social Sentiment</p>
                  <Skeleton className="h-5 w-16 mt-1" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <p className="text-sm text-muted-foreground text-center py-4">
        Report data will be loaded from the backend API
      </p>
    </div>
  );
}
