import { ssrPage } from "./_ssr.js";
// /partido?id=ID  (Pages redirige /partido.html → /partido). SSR del detalle de partido.
export const onRequest = (context) =>
  ssrPage(context, { json: "partidos.json", param: "id", type: "partido", div: "match" });
