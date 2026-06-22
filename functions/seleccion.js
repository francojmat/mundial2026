import { ssrPage } from "./_ssr.js";
// /seleccion?t=PAIS  → SSR del perfil de selección.
export const onRequest = (context) =>
  ssrPage(context, { json: "selecciones.json", param: "t", type: "seleccion", div: "sel" });
