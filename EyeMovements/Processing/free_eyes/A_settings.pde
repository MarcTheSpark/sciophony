int RETRATO_NUM = 191;
int CANTIDAD_OBSERVERS_ojo_3840 = 30; // the number of observers available for this portait;

float SCALE = 1;  // scaling factor for drawing

float DATA_DT = 0.002;  // 2 ms between data readings

float playbackRate = 1.0;  // playback rate;
float currentTime = 0.0;  // current time for data reading purposes (rate can change dynamically)
int lastMillis = -1; // last recorded value of millis()

int ALTO_PANTALLA = (int)(1000 * SCALE);
int ANCHO_PANTALLA = (int)(565 * SCALE);

float minDataX = 0;
float maxDataX = 2160.0;
float minDataY = 0;
float maxDataY = 3840.0;
