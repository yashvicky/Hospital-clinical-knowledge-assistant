import React from "react";
import { FileText, FileSearch } from "lucide-react";

import { CitationData } from "@/hooks/useClinicalQuery";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

interface DocumentPanelProps {
  citation: CitationData | null;
}

export const DocumentPanel: React.FC<DocumentPanelProps> = ({ citation }) => {
  if (!citation) {
    return (
      <div className="flex h-full flex-col items-center justify-center border-l bg-muted/40 p-8 text-muted-foreground">
        <FileSearch className="mb-4 h-16 w-16 text-muted-foreground/40" />
        <p className="text-center font-medium">No document selected</p>
        <p className="mt-2 text-center text-sm">
          Click a citation tag in the response to verify the clinical source.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col border-l bg-background shadow-sm">
      <div className="flex items-center justify-between border-b bg-muted/50 px-4 py-3">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <FileText className="h-4 w-4 text-primary" />
            Source Verification
          </h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Document ID:{" "}
            <span className="font-mono text-primary">{citation.docId}</span>
          </p>
        </div>
        <Badge variant="secondary">Page {citation.page}</Badge>
      </div>

      <div className="flex-1 overflow-y-auto bg-muted/40 p-6">
        <Card className="flex h-full flex-col items-center justify-center p-6 text-muted-foreground">
          <p className="font-mono text-sm">[PDF Render Placeholder]</p>
          <p className="mt-2 text-center text-xs">
            Fetching chunk matching {citation.docId}...
          </p>
        </Card>
      </div>
    </div>
  );
};
