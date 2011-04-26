import random
import sys
import time

def mat_mul(a,b,c,N):
	for i in xrange(N):
		for j in xrange(N):
			c[i][j] = 0.0
			for k in xrange(N):
				c[i][j] += a[i][k] * b[k][j]
	
N = int(sys.argv[1])

start = time.time()
a = [[random.random() for x in xrange(N)] for x in xrange(N)]
b = [[random.random() for x in xrange(N)] for x in xrange(N)]
c = [[0]*N for x in xrange(N)]
print 'Initialization time: {0:.4f} secs'.format(time.time() - start)

start = time.time()
mat_mul(a,b,c,N)
print 'Multiplication time: {0:.4f} secs'.format(time.time() - start)
