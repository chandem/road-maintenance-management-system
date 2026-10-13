import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { User } from "@supabase/supabase-js";
import { supabase } from "./lib/supabase";
import MaterialsModule from "./components/MaterialsModule";
import RoadInspectionsModule from "./components/RoadInspectionsModule";
import DepartmentWorkspace from "./components/DepartmentWorkspace";

// RESTORE_MARKER - content too large; use push from shell instead
export default function App() {
  return <div className="app-shell"><p>App restore in progress</p></div>;
}
