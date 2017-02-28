import numpy as np
from astropy.io import fits
import time
import trident
import datetime

ldb = trident.LineDatabase('lines.txt')


def write_header(ray,start_pos=None,end_pos=None,lines=None,author='NAME'):
	## begin making fits header
    prihdr = fits.Header()
    prihdr['AUTHOR'] = author
    prihdr['DATE'] = datetime.datetime.now().isoformat() ## from Scott
    prihdr['RAYSTART'] = str(start_pos)
    prihdr['RAYEND'] = str(end_pos)
    prihdr['SIM_NAME'] = ray.basename
    prihdr['NLINES'] = str(len(np.array(lines)))    

    lines = ldb.parse_subset(lines)
    
    i = 1
    for line in lines:
        keyword = 'LINE_'+str(i)
        prihdr[keyword] = line.name
        i += 1
    prihdu = fits.PrimaryHDU(header=prihdr)
    sghdulist = fits.HDUList([prihdu])
    return sghdulist

def write_parameter_file(filename,hdulist=None):
    if type(hdulist) != fits.hdu.hdulist.HDUList:
        raise ValueError('Must pass HDUList in order to write. Call write_header first.')

    param_file = np.genfromtxt(filename,delimiter='=',dtype=str,autostrip=True)
    col1 = fits.Column(name='PARAMETERS',format='A50',array=param_file[:,0])
    col2 = fits.Column(name='VALUES',format='A50',array=param_file[:,1])
    col_list = [col1,col2]

    cols = fits.ColDefs(col_list)
    sghdr = fits.Header()
    sghdr['SIM_CODE'] = 'enzo'
    sghdr['COMPUTER'] = 'pleiades'

    sghdu = fits.BinTableHDU.from_columns(cols,header=sghdr,name='PARAMS')
    hdulist.append(sghdu)    

    return

def generate_line(ray,line,write=False,hdulist=None):
    if (write == True) & ((type(hdulist) != fits.hdu.hdulist.HDUList)):
       raise ValueError('Must pass HDUList in order to write. Call write_header first.')

    if not isinstance(line,trident.Line):
        ldb = trident.LineDatabase('lines.txt')
        line_out = ldb.parse_subset(line)
        line_out = line_out[0]

    ar = ray.all_data()
    lambda_rest = line_out.wavelength
    lambda_min = lambda_rest * (1+min(ar['redshift_eff'])) - 1
    lambda_max = lambda_rest * (1+max(ar['redshift_eff'])) + 1

    sg = trident.SpectrumGenerator(lambda_min=lambda_min.value, lambda_max=lambda_max.value, dlambda=0.01)
    sg.make_spectrum(ray,lines=line_out.name)

    if write:
    	col1 = fits.Column(name='wavelength', format='E', array=sg.lambda_field,unit='Angstrom')
    	col2 = fits.Column(name='tau', format='E', array=sg.tau_field)
    	col3 = fits.Column(name='flux', format='E', array=sg.flux_field)
    	col_list = [col1,col2,col3]

    	for key in sg.line_observables[line_out.identifier].keys():
    	    col = fits.Column(name='sim_'+key,format='E',array=sg.line_observables[line_out.identifier][key])
    	    col_list = np.append(col_list,col)

    	cols = fits.ColDefs(col_list)
    	sghdr = fits.Header()
    	sghdr['LINENAME'] = line_out.identifier
    	sghdr['RESTWAVE'] = line_out.wavelength
    	sghdr['F_VALUE'] = line_out.f_value
    	sghdr['GAMMA'] = line_out.gamma

        ## want to leave blank spaces now for values that we're expecting to generate for MAST
        ## first let's add some spaces for the simulated, tau-weighted values!
        sghdr['SIM_TAU_HDENS'] = -9999.
        sghdr['SIM_TAU_TEMP'] = -9999.
        sghdr['SIM_TAU_METAL'] = -9999.

        ## we're also going to want data from Nick's fitting code
        ## it's going to give values for all of it's components
        ## for now, let's give it five and assume that many are going to be empty
        sghdr['NCOMPONENTS'] = 5.
        names = ['fit_EW','fit_coldens','fit_vcenter','fit_b','fit_delv90']
        ncomponent_standard = 5
        j = 0
        while j < ncomponent_standard:
            for name in names:
                stringin = name+str(j)
                sghdr[stringin] = -9999.
            j = j + 1

    	sghdu = fits.BinTableHDU.from_columns(cols,header=sghdr,name=line_out.name)

    	hdulist.append(sghdu)

    return sg

def write_out(hdulist,filename='spectrum.fits'):
	hdulist.writeto(filename, overwrite=True)
	return