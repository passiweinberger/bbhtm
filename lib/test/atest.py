import numpy as np
import matplotlib.pylab as plt
from temporal_memory import *
from pattern_lang import PatternLang
from scalar_encoder import *
from scalar_classifier import *
from stats import stats
import utils
from data_sets import *
import logging as log
import datetime as dt


class ATest:

	def __init__(self, name, data, results, data_size=100, nrows=5, winp=0.02, randomize=0.01, delta=False, loopy_cols=True) :

		self.data = data
		self.results = results
		self.test_name = name
		self.tame_taken = 0

		vmin = self.data.get('delta_min') if delta else self.data.get('min')
		vmax = self.data.get('delta_max') if delta else self.data.get('max')
		granularity = self.data.get('delta_granularity') if delta else self.data.get('granularity')
		self.tm = TemporalMemory(data_size=data_size, nrows=nrows, winp=winp, randomize=randomize, loopy_cols=loopy_cols)
		self.se = ScalarEncoder(minimum=vmin, maximum=vmax,nbits=data_size,width=self.tm.winners_count)
		self.sc = ScalarClassifier(encoder=self.se)
		#data for measuring performance
		self.ys = []
		self.yhat = []
		#init
		self.sc.build_cmap(start=vmin, end=vmax, step=granularity)

	def save(self, file_name):
		self.tm.save(file_name)
		self.se.save(file_name)
		self.sc.save(file_name)

	def load(self):
		raise NotImplementedError

	def run(self, name=None, begin=0,end=100,anim=False,run_metrics=True,via=False,forward=0,delta=False):
		self.end = end
		if name is not None : self.test_name = name
		self.ys = np.zeros(end-begin + forward, dtype=np.int)
		self.yhat = np.zeros(end-begin + forward, dtype=np.int)

		pred = self.se.encode(0)
	  	ds = self.data.data[begin:end]
		if delta :
			ds = self.data.delta[begin:end]

		ts = dt.datetime.now()

		for i, d in enumerate( ds ) :
			value = utils.np2bits( self.se.encode(d) )
			self.ys[i] = d #store the original data
			log.debug("%s> %s <=> %s : %s" % (i, d, self.yhat[i], self.yhat[i] - d) )

			if via : self.tm.via(value)
			else :  self.tm.train(value,anim=anim)

			#fetch last prediction
			pred = self.tm.predicted_sdr()
			if i < self.yhat.size - 1 :
				bm = self.sc.best_match(pred)
				self.yhat[i+1] = bm #save prediction one step forward

			if anim : self.tm.plot(pause=0.01,cmap='Greys')

		if forward > 0 :#predict more steps in the future
			for f in xrange(1,forward):
				tmp = next(self.tm.forward())
				self.yhat[end+f] = self.sc.best_match( tmp )
				log.debug( "fwd:%s> %s" % (f, self.yhat[end+f]) )

		te = dt.datetime.now()
		self.time_taken = te - ts
		log.debug("Time taken : %s" % self.time_taken)

		if run_metrics : self.metrics(forward=forward)


	def metrics(self, name=None, begin=0, end=None, forward=0):
		if name is None : name = self.test_name
		if end is None : end = self.ys.size
		self.results.add_data(name, self.ys, self.yhat, begin,end,forward)
		self.results.add_metric(name, 'fill', self.tm.memory.mem.fill)
		self.results.add_metric(name, 'avg_fill', self.tm.memory.mem.avg_item_fill)
		self.results.add_metric(name, 'max_fill', self.tm.memory.mem.max_item_fill)
		self.results.add_metric(name, 'time_taken', self.time_taken)

		self.results.print_metrics()


#==========================================================================================

	@staticmethod
	def rolling_metric(ys,yhat,fun=stats.mape,begin=10,step=10):
		assert ys is not None, "No data ....."
		size = ys.size
		return [ fun(ys[0:n],yhat[0:n]) for n in range(begin,size,step) ]


	@staticmethod
	def plot_metric(results=None, name=None, fun=stats.mape, begin=10, step=10, ys=None, yhat=None):
		if (results is not None) and (name is not None) :
			ys = results.series[name]['ys']
			yhat = results.series[name]['yhat']

		assert ys is not None, "No data ....."
		size = ys.size
		plt.plot(xrange(begin,size,step), ATest.rolling_metric(ys,yhat,fun,begin,step))

	def plot_data(self,full_fname=None, dpi=300, ys=None, yhat=None):
		name = self.test_name
		if ys is not None : ys_data = ys
		else : ys_data = self.results.series[name]['ys']
		if yhat is not None : yhat_data = yhat
		else: yhat_data = self.results.series[name]['yhat']

		fig = plt.figure()
		ax = fig.add_subplot(111)

		plt.plot(ys_data)
		plt.plot(yhat_data)

		if ys is None :
			fig.suptitle("%s | wp:%s,lc:%s" % (name,self.tm.winners_percent,self.tm.loopy_cols))
			y = 0.998
			for m in ['mape','nll', 'mae', 'rmse', 'r2'] :
				metric = "%s: %.3f" % (str(m).upper(), self.results.metrics[name][m])
				plt.text(0.998,y, metric, horizontalalignment='right',  verticalalignment='top', transform=ax.transAxes)
				y -= 0.03

		plt.tight_layout()
		if full_fname is not None :
			fig.savefig(full_fname,bbox_inches='tight',dpi=dpi)
			plt.close(fig)


	def generate_full_path(self, file_name, save_at='../tmp/dt', ext='svg') :
		tstamp = time.strftime('%d%H%M') + '-' + str(self.end) + '_'
		full = save_at + '/' + tstamp + file_name + '.' + ext
		return full

	def save_plot(self,file_name, save_at='../tmp/dt', ext='svg', dpi=300):
		full = self.generate_full_path(file_name, save_at, ext)
		log.debug( "Saving plot : %s" % full )
		self.plot_data(full, dpi=dpi)


