// Loads the real Google Picker JS SDK and opens the native Drive picker.
// Requires: OAuth access token (from our backend), a browser API key
// (developerKey) and the OAuth client's app id (GCP project number).
//
// openGoogleDrivePicker({ accessToken, apiKey, appId, onPicked })
//   onPicked receives an array of { id, name, mimeType } for selected files.

let _apiLoaded = false;
let _pickerLoaded = false;

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) return resolve();
    const s = document.createElement("script");
    s.src = src;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(s);
  });
}

async function ensureGapiPicker() {
  if (!_apiLoaded) {
    await loadScript("https://apis.google.com/js/api.js");
    _apiLoaded = true;
  }
  if (!_pickerLoaded) {
    await new Promise((resolve) => window.gapi.load("picker", { callback: resolve }));
    _pickerLoaded = true;
  }
}

export async function openGoogleDrivePicker({ accessToken, apiKey, appId, onPicked }) {
  if (!accessToken) throw new Error("Not connected to Google.");
  if (!apiKey) throw new Error("Google Picker API key is not configured.");
  await ensureGapiPicker();

  const google = window.google;
  const view = new google.picker.DocsView(google.picker.ViewId.DOCS)
    .setIncludeFolders(true)
    .setSelectFolderEnabled(false)
    .setMode(google.picker.DocsViewMode.LIST);

  const builder = new google.picker.PickerBuilder()
    .enableFeature(google.picker.Feature.MULTISELECT_ENABLED)
    .setOAuthToken(accessToken)
    .setDeveloperKey(apiKey)
    .addView(view)
    .addView(new google.picker.DocsView(google.picker.ViewId.PDFS))
    .addView(new google.picker.DocsView(google.picker.ViewId.SPREADSHEETS))
    .setCallback((data) => {
      if (data.action === google.picker.Action.PICKED) {
        const docs = (data.docs || []).map((d) => ({
          id: d.id, name: d.name, mimeType: d.mimeType,
        }));
        onPicked?.(docs);
      }
    });

  if (appId) builder.setAppId(appId);
  builder.build().setVisible(true);
}
