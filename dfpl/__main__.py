from argparse import Namespace
import pandas as pd
import importlib
import pathlib

from dfpl import dfpl
from dfpl import options
from dfpl import fingerprint as fp
from dfpl import autoencoder as ac
from dfpl import feedforwardNN as fnn

importlib.reload(dfpl)

project_directory = pathlib.Path(__file__).parent.parent.absolute()
test_train_args = options.TrainOptions(
    inputFile=f"{project_directory}/data/Sun_etal_dataset.csv",
    outputDir=f"{project_directory}/modeltraining",
    acFile="",
    type='smiles',
    fpType='topological',
    epochs=512,
    fpSize=2048,
    encFPSize=256,
    enableMultiLabel=False,
    testingFraction=0.2,
    kFolds=5,
    verbose=1
)


def train(opts: options.TrainOptions):
    """
    The function defining what happens in the main training procedure
    :param opts:
    """
    # read input and generate fingerprints from smiles
    df = fp.processInParallel(opts.inputFile, import_function=fp.importSmilesCSV, fp_size=opts.fpSize)

    encoder = None
    if opts.trainAC:
        # train an autoencoder on the full feature matrix
        encoder = ac.trainfullac(df, opts)
        encoder.save_weights(opts.acFile)
    else:
        # load trained model for autoencoder
        (autoencoder, encoder) = ac.autoencoderModel(input_size=opts.fpSize, encoding_dim=opts.encFPSize)
        encoder.load_weights(opts.acFile)

    # compress the fingerprints using the autoencoder
    df = ac.compressfingerprints(df, encoder)

    # train FNNs with compressed features
    fnn.trainNNmodels(df=df, opts=opts, usecompressed=True)

    # train FNNs with uncompressed features
    fnn.trainNNmodels(df=df, opts=opts, usecompressed=False)

    ### train multi-label models
    # with comrpessed features
    # dfpl.trainNNmodelsMulti(modelfilepathprefix=args.o + "/FNNmultiLabelmodelACincl",
    #                         x=xcompressed, y=ymatrix,
    #                         split=args.l, epochs=args.e,
    #                         verbose=args.v, kfold=args.K)

    # with uncompressed features
    # dfpl.trainNNmodelsMulti(modelfilepathprefix=opts.o + "/FNNmultiLabelmodelNoACincl",
    #                         x=xmatrix, y=ymatrix,
    #                         split=opts.l, epochs=opts.e,
    #                         verbose=opts.v, kfold=opts.K)


# ------------------------------------------------------------------------------------- #
## The function defining what happens in the main predict procedure 

def predict(args: Namespace) -> None:
    # generate X matrix
    (xpd, ymatrix) = dfpl.XandYfromInput(csvfilename=args.i, rtype=args.t, fptype=args.k,
                                         printfp=True, size=args.s, verbose=args.v, returnY=False)
    # predict values for provided data and model
    # ypredictions = dfpl.predictValues(modelfilepath="/data/bioinf/projects/data/2019_IDA-chem/deepFPlearn/modeltraining/2019-10-16_311681247_1000/model.Aromatase.h5", pdx=xpd)
    ypredictions = dfpl.predictValues(acmodelfilepath=args.ACmodel, modelfilepath=args.model, pdx=xpd)

    # write predictions to usr provided .csv file
    pd.DataFrame.to_csv(ypredictions, args.o)


# ===================================================================================== #

if __name__ == '__main__':
    parser = options.createCommandlineParser()
    prog_args = parser.parse_args()
    print(f"[INFO] The following arguments are received or filled with default values:\n{prog_args}")

    if prog_args.method == "train":
        train(options.TrainOptions.fromCmdArgs(prog_args))
        exit(0)
    if prog_args.method == "predict":
        predict(prog_args)
        exit(0)
    # Fallthrough
    print("uhh, what happened here?")
