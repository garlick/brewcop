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
/* pot.c - cchat agent to monitor Trent's coffee pot */

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <termios.h>
#include <errno.h>
#include <libgen.h>
#include <zmq.h>
#include <czmq.h>

#include "scale.h"
#include "log.h"
#include "util.h"

typedef struct {
	char *name;
	char *scaledev;
	FILE *scale;
	float full_lbs;
	float empty_lbs;
	int pct;
	int pct_err;
} pot_t;

static char *get_conf_str (zhash_t *conf, const char *name)
{
	char *s;
	if (!(s = zhash_lookup (conf, name)))
		msg_exit ("%s undefined", name);
	return xstrdup (s);
}

static float get_conf_num (zhash_t *conf, const char *name)
{
	char *s;
	if (!(s = zhash_lookup (conf, name)))
		msg_exit ("%s undefined", name);
	return strtof (s, NULL);
}

pot_t *pot_init (const char *filename)
{
	pot_t *pot = xzmalloc (sizeof (pot_t));
	zhash_t *conf;
	char *s;

	/* Read config file.
	 */
	if (!(conf = zhash_new ()))
		err_exit ("zhash_new");
	zhash_autofree (conf);
	if (zhash_load (conf, (char *)filename) < 0)
		err_exit ("error loading %s", filename);
	pot->name = get_conf_str (conf, "name");
	pot->scaledev = get_conf_str (conf, "scale_device");
	pot->full_lbs = get_conf_num (conf, "full_lbs");
	pot->empty_lbs = get_conf_num (conf, "empty_lbs");
	pot->pct_err = (int)get_conf_num (conf, "pct_err");
	zhash_destroy (&conf);

	/* Connect to scale.
	 */
	msg ("Initializing %s using scale on %s", pot->name, pot->scaledev);
	if (!(pot->scale = scale_init (pot->scaledev)))
		err_exit ("%s", pot->scaledev);

	return pot;
}

void pot_fini (pot_t *pot)
{
	if (pot->scale)
		scale_fini (pot->scale);
	if (pot->scaledev)
		free (pot->scaledev);
	if (pot->name)
		free (pot->name);
	free (pot);
}

void pot_update (pot_t *pot, int pct)
{
	int age_min = 0;

	if (pct < 0 && pot->pct >= 0)
		msg ("off");
	else if (pct >= 0 && pot->pct <= 0)
		msg ("on (%d%% full)", pct);
	pot->pct = pct;
}

void pot_checker (pot_t *pot)
{
	float lbs;
	int pct;

	for (;;) {
		if (scale_read (pot->scale, &lbs) < 0) {
			err ("scale_read");
			return;	
		}
		pct = 100 * (lbs - pot->empty_lbs)
			  / (pot->full_lbs - pot->empty_lbs);
		//msg ("read %.2f lbs (%d %%)", lbs, pct);
		pot_update (pot, pct);

		sleep (1);
	}
}

int main (int argc, char *argv[])
{
	pot_t *pot;
	char *scaledev;

	log_init (basename (argv[0]));
	pot = pot_init ("pot.conf");

	pot_checker (pot);

	pot_fini (pot);
	log_fini ();
	return 0;
}
