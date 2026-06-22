import { ssrPage } from "./_ssr.js";
// /plantel?t=PAIS  → SSR del plantel.
export const onRequest = (context) =>
  ssrPage(context, { json: "planteles.json", param: "t", type: "plantel", div: "squad" });
