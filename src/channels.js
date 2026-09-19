export const channelDefaults = {
  instagram: { source: 'instagram', medium: 'organic_social', campaign: 'profile' },
  facebook: { source: 'facebook', medium: 'organic_social', campaign: 'page' },
  meta: { source: 'meta', medium: 'paid_social', campaign: 'paid' },
  google: { source: 'google', medium: 'cpc', campaign: 'paid' },
  gbp: { source: 'google_business_profile', medium: 'organic_local', campaign: 'profile' },
  qr: { source: 'offline', medium: 'qr', campaign: 'restaurant' },
  direct: { source: 'direct', medium: 'owned_link', campaign: 'shared' },
};

export function applyChannelDefaults(url, channelKey) {
  const defaults = channelDefaults[channelKey];
  if (!defaults) return false;
  if (!url.searchParams.get('utm_source')) url.searchParams.set('utm_source', defaults.source);
  if (!url.searchParams.get('utm_medium')) url.searchParams.set('utm_medium', defaults.medium);
  if (!url.searchParams.get('utm_campaign')) url.searchParams.set('utm_campaign', defaults.campaign);
  return true;
}
