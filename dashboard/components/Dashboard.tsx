"use client";

import { useEffect, useState } from "react";
import { Activity, History, Mic, PhoneCall, Sparkles } from "lucide-react";

import { api, type Audit, type ScenarioInfo } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AuditPanel } from "@/components/AuditPanel";
import { CekuraPanel } from "@/components/CekuraPanel";
import { ImprovePanel } from "@/components/ImprovePanel";
import { LiveCall } from "@/components/LiveCall";
import { SessionsBrowser } from "@/components/SessionsBrowser";

export function Dashboard({
  initialAudit,
  initialScenarios,
}: {
  initialAudit: Audit | null;
  initialScenarios: ScenarioInfo[];
}) {
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>(initialScenarios);

  // If SSR couldn't reach the backend, hydrate the scenario list client-side.
  useEffect(() => {
    if (scenarios.length === 0) {
      api.scenarios().then(setScenarios).catch(() => undefined);
    }
  }, [scenarios.length]);

  return (
    <Tabs defaultValue="audit" className="w-full">
      <TabsList className="flex-wrap">
        <TabsTrigger value="audit">
          <Activity className="size-4" />
          Audit
        </TabsTrigger>
        <TabsTrigger value="live">
          <Mic className="size-4" />
          Live call
        </TabsTrigger>
        <TabsTrigger value="improve">
          <Sparkles className="size-4" />
          Improve
        </TabsTrigger>
        <TabsTrigger value="cekura">
          <PhoneCall className="size-4" />
          Cekura
        </TabsTrigger>
        <TabsTrigger value="sessions">
          <History className="size-4" />
          Sessions
        </TabsTrigger>
      </TabsList>

      <TabsContent value="audit">
        <AuditPanel scenarios={scenarios} initialAudit={initialAudit} />
      </TabsContent>
      <TabsContent value="live">
        <LiveCall scenarios={scenarios} />
      </TabsContent>
      <TabsContent value="improve">
        <ImprovePanel scenarios={scenarios} />
      </TabsContent>
      <TabsContent value="cekura">
        <CekuraPanel scenarios={scenarios} />
      </TabsContent>
      <TabsContent value="sessions">
        <SessionsBrowser scenarios={scenarios} />
      </TabsContent>
    </Tabs>
  );
}
