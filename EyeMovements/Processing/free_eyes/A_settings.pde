/*
NOTE: this file name starts with A (and the others start with other letters) as a way 
of forcing processing to put the pieces together in that order. These settings need
to be defined before some of the stuff in the other files.
*/

int RETRATO_NUM = 191;
int CANTIDAD_OBSERVERS_ojo_3840 = 30; // the number of observers available for this portait;

float SCALE = 1;  // scaling factor for drawing

float DATA_DT = 0.002;  // 2 ms between data readings

float playbackRate = 1.0;  // playback rate;
float currentTime = 0.0;  // current time for data reading purposes (rate can change dynamically)
int lastMillis = -1; // last recorded value of millis()

int ALTO_PANTALLA = (int)(1000 * SCALE);
int ANCHO_PANTALLA = (int)(565 * SCALE);

int SUBFRAME_FACTOR = 4;  // frames to draw per frame (to increase trail resolution)

float minDataX = 0;
float maxDataX = 2160.0;
float minDataY = 0;
float maxDataY = 3840.0;
