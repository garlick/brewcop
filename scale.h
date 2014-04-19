/* Read the weight (lb) in 'wp', internally retrying while scale is in motion.
 * On success, return 0.  On error, return -1 and set errno, e.g.
 * ERANGE: Scale over capacity / under capacity 
 * EDOM: Scale zeroing error
 * EPROTO: Unexpected response from scale.
 */
int scale_read(FILE *fp, float *wp);

/* Open the scale on serial port 'devname', e.g. "/dev/ttyUSB0".
 * On success return FILE pointer.  On failure, return NULL and set errno.
 */
FILE *scale_init(char *devname);

/* Close the scale.
 */
void scale_fini (FILE *fp);
