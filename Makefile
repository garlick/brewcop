POTOBJS = pot.o scale.o log.o util.o

all: pot

pot: $(POTOBJS)
	$(CC) -o $@ $(POTOBJS) -lczmq -lzmq

clean:
	rm -f *.o scale
