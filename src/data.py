"""
Dataset classes for variable number of speakers
Author: Junzhe Zhu
"""
import numpy as np
import torch
import torch.utils.data as data
from scipy.io.wavfile import read
from time import time

class MixtureDataset(data.Dataset):
    def __init__(self, txtfile, sample_rate=8000, segment=4.0, cv_maxlen=8.0):
        """
        each line of textfile comes in the form of:
            filename1, dB1, filename2, dB2, ...
        """
        self.specs = np.loadtxt(txtfile, dtype = str) # the specification of what source audio files are in each example, and what their scales are
        self.root = "/ws/ifp-10_3/hasegawa/junzhez2/Variable_Speaker_Model/egs/wsj0/" # root of source file relative paths
        self.sample_rate = sample_rate
    def __len__(self):
        return len(self.specs)
    def __getitem__(self, idx):
        """
        Returns:
            sources: list of num_speakers sounds, each of a different length
            scales: list of num_speakers scales, in the same order as sources
        """
        spec = self.specs[idx]
        num_speakers = len(spec)//2 # supports any number of speakers in mixture
        sources = []
        scales = []
        for i in range(num_speakers):
            sr, sound = read(self.root + spec[i*2])
            assert sr == self.sample_rate,  'sampling rate is not %d'%self.sample_rate # during preprocessing all wavs are turned into 8000 sampling rate
            sources.append(sound)
            scales.append(10**(float(spec[i*2+1])/20)) # turn dB into amplitude scale
        max_len = max(*[len(source) for source in sources])
        return sources, scales

def _collate_fn(batch):
    """
    Args:
        batch: list, len(batch) = batch_size, each entry is a tuple of (sources, scales)
    Returns:
        mixtures_pad: B x T, torch.Tensor, padded mixtures
        ilens : B, torch.Tensor, length of each mixture before padding
        sources_pad: list of B Tensors, each C x T, where C is (possibly variable) number of source audios
    """
    ilens = [] # shape of mixtures
    mixtures = [] # mixtures, same length as longest source in whole batch
    sources_pad = [] # padded sources, same length as mixtures
    for sources, scales in batch: # compute length to pad to
        ilens.append(max(*[len(source) for source in sources]))

    maxlen = max(ilens) # compute length to pad to
    ilens = torch.Tensor(np.array(ilens)).float()

    for sources, scales in batch:
        source_pad = np.array([pad(audio, maxlen) for audio in sources]) # one example, CXT
        source_pad = torch.Tensor(source_pad).float() # pad sources in one example
        sources_pad.append(source_pad)
        mixture = torch.matmul(source_pad.T, torch.Tensor(scales)) # add sources according to scale for one example
        mixtures.append(mixture)

    mixtures = torch.stack(mixtures, dim = 0)

    return mixtures, ilens, sources_pad

def pad(audio, length):
    padded = np.zeros(length)
    padded[:len(audio)] = audio
    return padded



if __name__ == "__main__":
    dataset = MixtureDataset("/ws/ifp-10_3/hasegawa/junzhez2/Variable_Speaker_Model/csv/mixtures/mix_2_spk_tr.txt")
    dataloader = torch.utils.data.DataLoader(dataset, batch_size = 32, collate_fn = _collate_fn)
    for mixtures, ilens, sources_pad in dataloader:
        start = time()
        print(mixtures.shape, ilens.shape, torch.stack(sources_pad, dim = 0).shape)
        print(time() - start)
    print(len(dataset))