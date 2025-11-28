const fs = require('fs');
const yaml = require('js-yaml');
const { TwitterApi } = require('twitter-api-v2');

const AGENDA_FILE = 'agenda.yaml';

// --- 1. Autenticación con X ---
console.log("Iniciando cliente de X...");
const client = new TwitterApi({
  appKey: process.env.TWITTER_API_KEY,
  appSecret: process.env.TWITTER_API_KEY_SECRET,
  accessToken: process.env.TWITTER_ACCESS_TOKEN,
  accessSecret: process.env.TWITTER_ACCESS_TOKEN_SECRET,
});

const rwClient = client.readWrite;

// --- 2. Función para buscar el job de hoy ---
function getJobParaHoy() {
  const hoy = new Date().toISOString().split('T')[0]; // Formato YYYY-MM-DD
  console.log(`Buscando job para hoy: ${hoy}`);

  if (!fs.existsSync(AGENDA_FILE)) {
    console.warn(`Advertencia: El archivo ${AGENDA_FILE} no existe.`);
    return null;
  }

  const fileContents = fs.readFileSync(AGENDA_FILE, 'utf8');
  const data = yaml.load(fileContents);
  
  if (!data || !data.jobs || data.jobs.length === 0) {
    console.log("agenda.yaml está vacío o no tiene jobs.");
    return null;
  }

  const jobHoy = data.jobs.find(job => job.date === hoy);
  return jobHoy;
}

// --- ¡NUEVO! 3. Función para limpiar el job de la agenda ---
function removeJobFromAgenda(jobPublicado) {
  console.log(`Limpiando job [${jobPublicado.concept}] de la agenda...`);

  const fileContents = fs.readFileSync(AGENDA_FILE, 'utf8');
  const data = yaml.load(fileContents);

  // Filtramos la lista de jobs, quedándonos solo con los que NO coinciden
  // con la fecha Y el concepto del job que acabamos de publicar.
  const jobsPendientes = data.jobs.filter(job => {
    return !(job.date === jobPublicado.date && job.concept === jobPublicado.concept);
  });

  // Reconstruimos el objeto de datos
  const dataActualizada = { jobs: jobsPendientes };

  // Escribimos el archivo de vuelta al disco
  fs.writeFileSync(AGENDA_FILE, yaml.dump(dataActualizada), 'utf8');
  console.log("✅ agenda.yaml ha sido limpiada.");
}

// --- 4. Función principal (modificada) ---
async function publicarHilo() {
  let jobHoy = null; // La definimos fuera del try para usarla en el finally

  try {
    jobHoy = getJobParaHoy();

    if (jobHoy) {
      console.log(`Job encontrado para ${jobHoy.date}.`);
      console.log(`Concepto: ${jobHoy.concept}`);
      
      if (!Array.isArray(jobHoy.thread) || jobHoy.thread.length === 0) {
          throw new Error("El 'thread' en el YAML no es un array válido o está vacío.");
      }

      console.log(`Publicando hilo de ${jobHoy.thread.length} tweets...`);
      
      // --- Publicación en X ---
      await rwClient.v2.tweetThread(jobHoy.thread);

      console.log("--- ¡ÉXITO! ---");
      console.log("El hilo ha sido publicado en X.");
      console.log("Primer tweet:", jobHoy.thread[0]);
      
      // --- ¡NUEVO! Llamada a la limpieza ---
      // Solo si la publicación fue exitosa, limpiamos el job.
      removeJobFromAgenda(jobHoy);

    } else {
      console.log("No hay ningún job programado en la agenda para hoy. Saliendo limpiamente.");
    }
  } catch (error) {
    console.error("--- ¡ERROR AL PUBLICAR! ---");
    console.error("Detalles del error:", error.message || error);
    process.exit(1); // Forzamos el fallo del workflow
  }
}

// --- 5. Ejecutar el script ---
publicarHilo();
