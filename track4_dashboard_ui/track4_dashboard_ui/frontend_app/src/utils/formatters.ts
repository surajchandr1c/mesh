export const formatDate = (isoString: string): string => {
  if (!isoString) return 'N/A';
  try {
    const date = new Date(isoString);
    return date.toLocaleString();
  } catch (_) {
    return isoString;
  }
};
