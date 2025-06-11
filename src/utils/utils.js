// Utility functions for the Moodify app

export function cn(...inputs) {
  // Simple className merger - simplified version without external dependencies
  return inputs.filter(Boolean).join(' ');
}

export function createPageUrl(pageName, params = {}) {
  let url = `/${pageName.toLowerCase()}`;
  
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, value.toString());
    }
  });
  
  const queryString = searchParams.toString();
  if (queryString) {
    url += `?${queryString}`;
  }
  
  return url;
}