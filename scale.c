/*****************************************************************************
 *  Copyright (C) 2014 Jim Garlick
 *  Written by Jim Garlick <garlick.jim@gmail.com>
 *  All Rights Reserved.
 *
 *  This file is part of cchat
 *  For details, see <https://github.com/garlick/cchat>
 *
 *  This program is free software; you can redistribute it and/or modify it
 *  under the terms of the GNU General Public License (as published by the
 *  Free Software Foundation) version 2, dated June 1991.
 *
 *  This program is distributed in the hope that it will be useful, but
 *  WITHOUT ANY WARRANTY; without even the IMPLIED WARRANTY OF MERCHANTABILITY
 *  or FITNESS FOR A PARTICULAR PURPOSE. See the terms and conditions of the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software Foundation,
 *  Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA or see
 *  <http://www.gnu.org/licenses/>.
 *****************************************************************************/
/* scale.c - read Avery-Berkel 6702-16658 bench scale */

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <termios.h>
#include <errno.h>

#include "scale.h"

int scale_read(FILE *fp, float *wp)
{
	int n, status;
	float weight;
again:
	if (fputs ("W\r", fp) < 0)
		goto error;
	if (fscanf (fp, "\n%fLB\r\nS%d\r\003", &weight, &status) == 2)
		goto done;
	/* over capacity */
	if (fscanf (fp, "\n^^^^^^\r\nS%d\r\003", &status) == 1) {
		errno = ERANGE;
		goto error;
	}
	/* under capacity */
	if (fscanf (fp, "\n______\r\nS%d\r\003", &status) == 1) {
		errno = ERANGE;
		goto error;
	}
	/* zeroing error */
	if (fscanf (fp, "\n------\r\nS%d\r\003", &status) == 1) {
		errno = EDOM;
		goto error;
	}
	/* status only (e.g. scale in motion) */
	if (fscanf (fp, "\nS%d\r\003", &status) == 1)
		goto again;
	/* Unknown response */
	errno = EPROTO;
error:
	return -1;

done:
	//*wp = weight * 0.453592; /* lbs to kg */
	*wp = weight;
	return 0;
}

FILE *scale_init(char *devname)
{
	int fd;
	struct termios tio;

	if ((fd = open(devname, O_RDWR)) < 0)
		goto error;
	if (flock(fd, LOCK_EX | LOCK_NB) < 0)
		goto error;
	if (tcgetattr(fd, &tio) < 0)
		goto error;
	cfsetspeed(&tio, B9600);/* 9600 baud */
	tio.c_cflag &= ~CSIZE;	/* 7 bits */
	tio.c_cflag |= CS7;
	tio.c_cflag &= ~CSTOPB;	/* 1 stop bit */
	tio.c_cflag |= PARENB;	/* enable parity */
	tio.c_cflag &= ~PARODD;	/* use even parity */
	if (tcsetattr(fd, TCSANOW, &tio) < 0)
		goto error;
	return fdopen (fd, "r+");
error:
	if (fd >= 0)
		close (fd);
	return NULL;
}

void scale_fini (FILE *fp)
{
	fclose (fp);
}

#if 0
int main (int argc, char *argv[])
{
	FILE *fp;
	float weight;

	if (!(fp = scale_init ("/dev/ttyUSB0"))) {
		perror ("/dev/ttyUSB0");
		return 1;
	}

	if (scale_read (fp, &weight) < 0) {
		perror ("scale_read");
		return 1;
	}

	printf ("Weight: %flbs\n", weight);
	
	scale_fini (fp);
	return 0;
}
#endif
