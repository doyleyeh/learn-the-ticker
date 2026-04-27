export function configuredApiBaseUrl(): string | null {
  const configuredBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || process.env.API_BASE_URL?.trim();
  if (configuredBaseUrl) {
    return configuredBaseUrl;
  }

  if (process.env.NODE_ENV !== "production") {
    return "http://127.0.0.1:8000";
  }

  return null;
}

export function publicApiEndpoint(relativeUrl: string): string {
  const apiBaseUrl = configuredApiBaseUrl();
  if (!apiBaseUrl) {
    return relativeUrl;
  }

  return new URL(relativeUrl, apiBaseUrl).toString();
}

export function requiredApiEndpoint(relativeUrl: string, missingApiBaseMessage: string): string {
  const apiBaseUrl = configuredApiBaseUrl();
  if (!apiBaseUrl) {
    throw new Error(missingApiBaseMessage);
  }

  return new URL(relativeUrl, apiBaseUrl).toString();
}
