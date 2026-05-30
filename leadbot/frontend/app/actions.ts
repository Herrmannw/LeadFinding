"use server";

import { redirect } from "next/navigation";
import { createSearchJob, normalizeSources } from "@/lib/leadbot";

export async function createSearchJobAction(formData: FormData) {
  const industry = stringValue(formData.get("industry"));
  const location = stringValue(formData.get("location"));
  const targetRecordCount = numberValue(formData.get("target_record_count"));
  const selectedSources = normalizeSources(
    formData.getAll("selected_sources").map((value) => String(value)),
  );

  if (!industry || !location) {
    redirect("/?error=missing-fields");
  }

  if (!Number.isInteger(targetRecordCount) || targetRecordCount < 1 || targetRecordCount > 5000) {
    redirect("/?error=invalid-target");
  }

  const job = await createSearchJob({
    industry,
    location,
    targetRecordCount,
    selectedSources,
  });

  redirect(`/jobs/${job.id}`);
}

function stringValue(value: FormDataEntryValue | null) {
  return typeof value === "string" ? value.trim() : "";
}

function numberValue(value: FormDataEntryValue | null) {
  if (typeof value !== "string") {
    return Number.NaN;
  }
  return Number(value);
}
