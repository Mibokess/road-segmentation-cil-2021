"""
In this file are the layers and blocks contained which are used by the models in model.py.  
The main block types are convolutional, dilated and spatial.  
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from init_weights import init_weights
from torch.nn import GRUCell

# UNet3+
# form https://github.com/ZJUGiveLab/UNet-Version/blob/8ecd06740d18cf508e5c8b2cc2bf38a026aa0e9b/models/layers.py

class unetConv2Spatial(nn.Module):
    def __init__(self, in_size, out_size, is_batchnorm, n=2, ks=3, stride=1, padding=1, upsample=False):
        super(unetConv2Spatial, self).__init__()
        self.n = n
        self.ks = ks
        self.stride = stride
        self.padding = padding
        s = stride
        p = padding
        if is_batchnorm:
            for i in range(1, n):
                conv = nn.Sequential(nn.Conv2d(in_size, out_size, ks, s, p),
                                     nn.BatchNorm2d(out_size),
                                     nn.ReLU(inplace=True), )
                setattr(self, 'conv%d' % i, conv)
                in_size = out_size
            
            for i in range(n, n + 1):
                conv = nn.Sequential(ResSDNLayer(in_size, out_size, 16, range(4), 3, 1, 1, upsample),
                                     nn.BatchNorm2d(out_size),
                                     nn.ReLU(inplace=True), )
                setattr(self, 'conv%d' % i, conv)
                in_size = out_size

        else:
            for i in range(1, n + 1):
                conv = nn.Sequential(nn.Conv2d(in_size, out_size, ks, s, p),
                                     nn.ReLU(inplace=True), )
                setattr(self, 'conv%d' % i, conv)
                in_size = out_size

        # initialise the blocks
        for m in self.children():
            init_weights(m, init_type='kaiming')

    def forward(self, inputs):
        x = inputs
        for i in range(1, self.n + 1):
            conv = getattr(self, 'conv%d' % i)
            x = conv(x)

        return x
    
class unetConv2Dilated(nn.Module):
    def __init__(self, in_size, out_size, is_batchnorm, n=2, ks=3, stride=1, padding=1, upsample=False):
        super(unetConv2Dilated, self).__init__()
        self.n = n
        self.ks = ks
        self.stride = stride
        self.padding = padding
        s = stride
        p = padding
        
        out_c = out_size
        self.is_bn = is_batchnorm
        
        if is_batchnorm:
            for i in range(1, n):
                conv = nn.Sequential(nn.Conv2d(in_size, out_size, ks, s, p),
                                     nn.BatchNorm2d(out_size),
                                     nn.ReLU(inplace=True), )
                setattr(self, 'conv%d' % i, conv)
                in_size = out_size
            
            self.dial_conv1 = nn.Conv2d(out_c, out_c//2, kernel_size=3, padding=1)
            self.bn1 = nn.BatchNorm2d(out_c//2)
            
            self.dial3 = nn.Conv2d(out_c//2, out_c//4, kernel_size=3, padding=3, dilation=3)
            self.bn2_1 = nn.BatchNorm2d(out_c//4)

            self.dial6 = nn.Conv2d(out_c//4, out_c//8, kernel_size=3, padding=6, dilation=6)
            self.bn2_2 = nn.BatchNorm2d(out_c//8)

            self.dial9 = nn.Conv2d(out_c//8, out_c//16, kernel_size=3, padding=9, dilation=9)
            self.bn2_3 = nn.BatchNorm2d(out_c//16)

            self.dial12 = nn.Conv2d(out_c//16, out_c//16, kernel_size=3, padding=12, dilation=12)
            self.bn2_4 = nn.BatchNorm2d(out_c//16)
            
            self.dial_conv2 = nn.Conv2d(out_c, out_c, kernel_size=3, padding=1)
            self.bn2 = nn.BatchNorm2d(out_c)        

            self.relu = nn.ReLU()
        
            in_size = out_size

        else:
            for i in range(1, n + 1):
                conv = nn.Sequential(nn.Conv2d(in_size, out_size, ks, s, p),
                                     nn.ReLU(inplace=True), )
                setattr(self, 'conv%d' % i, conv)
                in_size = out_size

        # initialise the blocks
        for m in self.children():
            init_weights(m, init_type='kaiming')

    def forward(self, inputs):
        x = inputs
        if self.is_bn:
            for i in range(1, self.n):
                conv = getattr(self, 'conv%d' % i)
                x = conv(x)
            
            x = self.dial_conv1(x)
            x = self.bn1(x)
            x = self.relu(x)
        
            z1=self.dial3(x)
            z1=self.bn2_1(z1)
            z1=self.relu(z1)

            z2=self.dial6(z1)
            z2=self.bn2_2(z2)
            z2=self.relu(z2)

            z3=self.dial9(z2)
            z3=self.bn2_3(z3)
            z3=self.relu(z3)

            z4=self.dial12(z3)
            z4=self.bn2_4(z4)
            z4=self.relu(z4)
        
            z = torch.cat([x, z1, z2, z3, z4], 1)
            
            x = self.dial_conv2(z)
            x = self.bn2(x)
            x = self.relu(x)
            
        else:
            for i in range(1, self.n + 1):
                conv = getattr(self, 'conv%d' % i)
                x = conv(x)

        return x

class unetConv2(nn.Module):
    def __init__(self, in_size, out_size, is_batchnorm, n=2, ks=3, stride=1, padding=1):
        super(unetConv2, self).__init__()
        self.n = n
        self.ks = ks
        self.stride = stride
        self.padding = padding
        s = stride
        p = padding
        if is_batchnorm:
            for i in range(1, n + 1):
                conv = nn.Sequential(nn.Conv2d(in_size, out_size, ks, s, p),
                                     nn.BatchNorm2d(out_size),
                                     nn.ReLU(inplace=True), )
                setattr(self, 'conv%d' % i, conv)
                in_size = out_size

        else:
            for i in range(1, n + 1):
                conv = nn.Sequential(nn.Conv2d(in_size, out_size, ks, s, p),
                                     nn.ReLU(inplace=True), )
                setattr(self, 'conv%d' % i, conv)
                in_size = out_size

        # initialise the blocks
        for m in self.children():
            init_weights(m, init_type='kaiming')

    def forward(self, inputs):
        x = inputs
        for i in range(1, self.n + 1):
            conv = getattr(self, 'conv%d' % i)
            x = conv(x)

        return x
    
class unetUp(nn.Module):
    def __init__(self, in_size, out_size, is_deconv, n_concat=2):
        super(unetUp, self).__init__()
        # self.conv = unetConv2(in_size + (n_concat - 2) * out_size, out_size, False)
        self.conv = unetConv2(out_size*2, out_size, False)
        if is_deconv:
            self.up = nn.ConvTranspose2d(in_size, out_size, kernel_size=4, stride=2, padding=1)
        else:
            self.up = nn.UpsamplingBilinear2d(scale_factor=2)

        # initialise the blocks
        for m in self.children():
            if m.__class__.__name__.find('unetConv2') != -1: continue
            init_weights(m, init_type='kaiming')

    def forward(self, inputs0, *input):
        # print(self.n_concat)
        # print(input)
        outputs0 = self.up(inputs0)
        for i in range(len(input)):
            outputs0 = torch.cat([outputs0, input[i]], 1)
        return self.conv(outputs0)
    
class unetUp_origin(nn.Module):
    def __init__(self, in_size, out_size, is_deconv, n_concat=2):
        super(unetUp_origin, self).__init__()
        # self.conv = unetConv2(out_size*2, out_size, False)
        if is_deconv:
            self.conv = unetConv2(in_size + (n_concat - 2) * out_size, out_size, False)
            self.up = nn.ConvTranspose2d(in_size, out_size, kernel_size=4, stride=2, padding=1)
        else:
            self.conv = unetConv2(in_size + (n_concat - 2) * out_size, out_size, False)
            self.up = nn.UpsamplingBilinear2d(scale_factor=2)

        # initialise the blocks
        for m in self.children():
            if m.__class__.__name__.find('unetConv2') != -1: continue
            init_weights(m, init_type='kaiming')

    def forward(self, inputs0, *input):
        # print(self.n_concat)
        # print(input)
        outputs0 = self.up(inputs0)
        for i in range(len(input)):
            outputs0 = torch.cat([outputs0, input[i]], 1)
        return self.conv(outputs0)

# UNet(++)
class dilated_spatial_block(nn.Module):
    def __init__(self, in_c, out_c, upsample=False):
        super().__init__()

        self.conv = nn.Conv2d(in_c, out_c//2, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(out_c//2)
        
        
        self.dial3 = nn.Conv2d(out_c//2, out_c//4, kernel_size=3, padding=3, dilation=3)
        self.bn2_1 = nn.BatchNorm2d(out_c//4)
        
        self.dial6 = nn.Conv2d(out_c//4, out_c//8, kernel_size=3, padding=6, dilation=6)
        self.bn2_2 = nn.BatchNorm2d(out_c//8)

        self.dial9 = nn.Conv2d(out_c//8, out_c//16, kernel_size=3, padding=9, dilation=9)
        self.bn2_3 = nn.BatchNorm2d(out_c//16)

        self.dial12 = nn.Conv2d(out_c//16, out_c//16, kernel_size=3, padding=12, dilation=12)
        self.bn2_4 = nn.BatchNorm2d(out_c//16)
        

        self.spatial = ResSDNLayer(out_c, out_c, 16, range(4), 3, 1, 1, upsample)
        self.bn3 = nn.BatchNorm2d(out_c)

        self.relu = nn.ReLU()

    def forward(self, inputs):
        x = self.conv(inputs)
        x = self.bn1(x)
        x = self.relu(x)
        #print(x.shape)
        
        z1=self.dial3(x)
        z1=self.bn2_1(z1)
        z1=self.relu(z1)
        #print(z1.shape)
        
        z2=self.dial6(z1)
        z2=self.bn2_2(z2)
        z2=self.relu(z2)
        #print(z2.shape)
        
        z3=self.dial9(z2)
        z3=self.bn2_3(z3)
        z3=self.relu(z3)
        #print(z3.shape)
        
        z4=self.dial12(z3)
        z4=self.bn2_4(z4)
        z4=self.relu(z4)
        #print(z4.shape)
        
        z = torch.cat([x, z1, z2, z3, z4], 1)

        x = self.spatial(z)
        x = self.bn3(x)
        x = self.relu(x)

        return x
    
class dilated_conv_block(nn.Module):
    def __init__(self, in_c, out_c):
        super().__init__()

        self.conv = nn.Conv2d(in_c, out_c//2, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(out_c//2)
        
        
        self.dial3 = nn.Conv2d(out_c//2, out_c//4, kernel_size=3, padding=3, dilation=3)
        self.bn2_1 = nn.BatchNorm2d(out_c//4)
        
        self.dial6 = nn.Conv2d(out_c//4, out_c//8, kernel_size=3, padding=6, dilation=6)
        self.bn2_2 = nn.BatchNorm2d(out_c//8)

        self.dial9 = nn.Conv2d(out_c//8, out_c//16, kernel_size=3, padding=9, dilation=9)
        self.bn2_3 = nn.BatchNorm2d(out_c//16)

        self.dial12 = nn.Conv2d(out_c//16, out_c//16, kernel_size=3, padding=12, dilation=12)
        self.bn2_4 = nn.BatchNorm2d(out_c//16)
        
        self.conv2 = nn.Conv2d(out_c, out_c, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(out_c)        

        self.relu = nn.ReLU()

    def forward(self, inputs):
        x = self.conv(inputs)
        x = self.bn1(x)
        x = self.relu(x)
        #print(x.shape)
        
        z1=self.dial3(x)
        z1=self.bn2_1(z1)
        z1=self.relu(z1)
        #print(z1.shape)
        
        z2=self.dial6(z1)
        z2=self.bn2_2(z2)
        z2=self.relu(z2)
        #print(z2.shape)
        
        z3=self.dial9(z2)
        z3=self.bn2_3(z3)
        z3=self.relu(z3)
        #print(z3.shape)
        
        z4=self.dial12(z3)
        z4=self.bn2_4(z4)
        z4=self.relu(z4)
        #print(z4.shape)
        
        z = torch.cat([x, z1, z2, z3, z4], 1)
        
        x = self.conv2(z)
        x = self.bn3(x)
        x = self.relu(x)

        return x
    
class dilated_block(nn.Module):
    def __init__(self, in_c, out_c):
        super().__init__()

        self.conv = nn.Conv2d(in_c, out_c//2, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(out_c//2)
        
        
        self.dial3 = nn.Conv2d(out_c//2, out_c//4, kernel_size=3, padding=3, dilation=3)
        self.bn2_1 = nn.BatchNorm2d(out_c//4)
        
        self.dial6 = nn.Conv2d(out_c//4, out_c//8, kernel_size=3, padding=6, dilation=6)
        self.bn2_2 = nn.BatchNorm2d(out_c//8)

        self.dial9 = nn.Conv2d(out_c//8, out_c//16, kernel_size=3, padding=9, dilation=9)
        self.bn2_3 = nn.BatchNorm2d(out_c//16)

        self.dial12 = nn.Conv2d(out_c//16, out_c//16, kernel_size=3, padding=12, dilation=12)
        self.bn2_4 = nn.BatchNorm2d(out_c//16)
        

        self.relu = nn.ReLU()

    def forward(self, inputs):
        x = self.conv(inputs)
        x = self.bn1(x)
        x = self.relu(x)
        #print(x.shape)
        
        z1=self.dial3(x)
        z1=self.bn2_1(z1)
        z1=self.relu(z1)
        #print(z1.shape)
        
        z2=self.dial6(z1)
        z2=self.bn2_2(z2)
        z2=self.relu(z2)
        #print(z2.shape)
        
        z3=self.dial9(z2)
        z3=self.bn2_3(z3)
        z3=self.relu(z3)
        #print(z3.shape)
        
        z4=self.dial12(z3)
        z4=self.bn2_4(z4)
        z4=self.relu(z4)
        #print(z4.shape)
        
        z = torch.cat([x, z1, z2, z3, z4], 1)

        return z
# from https://github.com/4uiiurz1/pytorch-nested-unet/blob/master/archs.py
class VGGSpatialBlock(nn.Module):
    def __init__(self, in_channels, middle_channels, out_channels, upsample=False):
        super().__init__()
        self.relu = nn.ReLU(inplace=True)
        self.conv1 = nn.Conv2d(in_channels, middle_channels, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(middle_channels)
                
        self.spatial = ResSDNLayer(middle_channels, out_channels, 16, range(4), 3, 1, 1, upsample)
        self.bn2 = nn.BatchNorm2d(out_channels)

    def forward(self, x):
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.spatial(out)
        out = self.bn2(out)
        out = self.relu(out)

        return out
    
class spatial_block(nn.Module):
    def __init__(self, in_c, out_c, upsample=False):
        super().__init__()

        self.conv = nn.Conv2d(in_c, out_c, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(out_c)

        self.spatial = ResSDNLayer(out_c, out_c, 16, range(4), 3, 1, 1, upsample)
        self.bn2 = nn.BatchNorm2d(out_c)

        self.relu = nn.ReLU()

    def forward(self, inputs):
        x = self.conv(inputs)
        x = self.bn1(x)
        x = self.relu(x)

        x = self.spatial(x)
        x = self.bn2(x)
        x = self.relu(x)

        return x

class VGGBlock(nn.Module):
    def __init__(self, in_channels, middle_channels, out_channels):
        super().__init__()
        self.relu = nn.ReLU(inplace=True)
        self.conv1 = nn.Conv2d(in_channels, middle_channels, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(middle_channels)
        self.conv2 = nn.Conv2d(middle_channels, out_channels, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(out_channels)

    def forward(self, x):
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        return out

class conv_block(nn.Module):
    def __init__(self, in_c, out_c):
        super().__init__()

        self.conv1 = nn.Conv2d(in_c, out_c, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(out_c)

        self.relu = nn.ReLU()

    def forward(self, inputs):
        x = self.conv1(inputs)
        x = self.bn1(x)
        x = self.relu(x)
        
        return x
    
# SDN
# from https://github.com/djordjemila/sdn/blob/main/lib/nn.py

class SDNCell(nn.Module):
    def __init__(self, num_features):
        super().__init__()
        self.gru = GRUCell(input_size=3*num_features, hidden_size=num_features)

    def forward(self, neighboring_features, features):
        """ Update current features based on neighboring features """
        return self.gru(torch.cat(neighboring_features, dim=1), features)

class _CorrectionLayer(nn.Module):

    def __init__(self, num_features, dir=0):
        super().__init__()
        self.num_features = num_features
        self.cell = SDNCell(num_features)
        if dir == 0:
            self.forward = self.forward0
        elif dir == 1:
            self.forward = self.forward1
        elif dir == 2:
            self.forward = self.forward2
        else:
            self.forward = self.forward3
        self.zero_pad = None

    def _get_zero_pad(self, batch, device):
        if self.zero_pad is None or self.zero_pad.shape[0] != batch:
            self.zero_pad = torch.zeros((batch, self.num_features, 1), device=device)  # no grad ??
        return self.zero_pad

    def forward0(self, features):
        batch = features.shape[0]
        dim = features.shape[2]
        zero_pad = self._get_zero_pad(batch, features.device)
        # make a loop
        for d in range(1, dim):
            neighboring_features = torch.cat([zero_pad, features[:, :, :, d - 1], zero_pad], dim=2).transpose(1, 2)
            # compute features
            features[:, :, :, d] = self.cell(
                neighboring_features=[neighboring_features[:, :-2, :].reshape(-1, self.num_features),
                                      neighboring_features[:, 1:-1, :].reshape(-1, self.num_features),
                                      neighboring_features[:, 2:, :].reshape(-1, self.num_features)],
                features=features[:, :, :, d].transpose(1, 2).reshape(-1, self.num_features).clone()
            ).reshape(batch, -1, self.num_features).transpose(1, 2)
        # return new features
        return features

    def forward1(self, features):
        batch = features.shape[0]
        dim = features.shape[2]
        zero_pad = self._get_zero_pad(batch, features.device)
        # make a loop
        for d in range(dim - 2, -1, -1):
            neighboring_features = torch.cat([zero_pad, features[:, :, :, d + 1], zero_pad], dim=2).transpose(1, 2)
            # compute features
            features[:, :, :, d] = self.cell(
                neighboring_features=[neighboring_features[:, :-2, :].reshape(-1, self.num_features),
                                      neighboring_features[:, 1:-1, :].reshape(-1, self.num_features),
                                      neighboring_features[:, 2:, :].reshape(-1, self.num_features)],
                features=features[:, :, :, d].transpose(1, 2).reshape(-1, self.num_features).clone()
            ).reshape(batch, -1, self.num_features).transpose(1, 2)
        # return new features
        return features

    def forward2(self, features):
        batch = features.shape[0]
        dim = features.shape[2]
        zero_pad = self._get_zero_pad(batch, features.device)
        # make a loop
        for d in range(1, dim):
            neighboring_features = torch.cat([zero_pad, features[:, :, d - 1, :], zero_pad], dim=2).transpose(1, 2)
            # compute features
            features[:, :, d, :] = self.cell(
                neighboring_features=[neighboring_features[:, :-2, :].reshape(-1, self.num_features),
                                      neighboring_features[:, 1:-1, :].reshape(-1, self.num_features),
                                      neighboring_features[:, 2:, :].reshape(-1, self.num_features)],
                features=features[:, :, d, :].transpose(1, 2).reshape(-1, self.num_features).clone()
            ).reshape(batch, -1, self.num_features).transpose(1, 2)
        # return new features
        return features

    def forward3(self, features):
        batch = features.shape[0]
        dim = features.shape[2]
        zero_pad = self._get_zero_pad(batch, features.device)
        # make a loop
        for d in range(dim - 2, -1, -1):
            neighboring_features = torch.cat([zero_pad, features[:, :, d + 1, :], zero_pad], dim=2).transpose(1, 2)
            # compute features
            features[:, :, d, :] = self.cell(
                neighboring_features=[neighboring_features[:, :-2, :].reshape(-1, self.num_features),
                                      neighboring_features[:, 1:-1, :].reshape(-1, self.num_features),
                                      neighboring_features[:, 2:, :].reshape(-1, self.num_features)],
                features=features[:, :, d, :].transpose(1, 2).reshape(-1, self.num_features).clone()
            ).reshape(batch, -1, self.num_features).transpose(1, 2)
        # return new features
        return features

class SDNLayer(nn.Module):
    def __init__(self, in_ch, out_ch, num_features, dirs, kernel_size, stride, padding, upsample):
        super().__init__()
        # project-in network
        cnn_module = nn.ConvTranspose2d if 2 else nn.Conv2d
        self.project_in_stage = cnn_module(in_ch, num_features, kernel_size, stride, padding)
        # correction network
        sdn_correction_layers = []
        for dir in dirs:
            sdn_correction_layers.append(_CorrectionLayer(num_features, dir=dir))
        self.sdn_correction_stage = nn.Sequential(*sdn_correction_layers)
        # project-out network
        self.project_out_stage = nn.Conv2d(num_features, out_ch, 1)

    def forward(self, x):
        # (I) project-in stage
        x = self.project_in_stage(x)
        x = torch.tanh(x)
        # (II) correction stage
        x = x.contiguous(memory_format=torch.channels_last)
        x = self.sdn_correction_stage(x)
        x = x.contiguous(memory_format=torch.contiguous_format)
        # (III) project-out stage
        x = self.project_out_stage(x)
        return x

class ResSDNLayer(nn.Module):
    def __init__(self, in_ch, out_ch, num_features, dirs, kernel_size, stride, padding, upsample):
        super().__init__()
        self.sdn = SDNLayer(in_ch, 2 * out_ch, num_features, dirs, kernel_size, stride, padding, upsample)
        cnn_module = nn.ConvTranspose2d if upsample else nn.Conv2d
        self.cnn = cnn_module(in_ch, out_ch, kernel_size, stride, padding)

    def forward(self, input):
        cnn_out = self.cnn(input)
        sdn_out, gate = self.sdn(input).chunk(2, 1)
        gate = torch.sigmoid(gate)
        return gate * cnn_out + (1-gate) * sdn_out

  

    def __init__(self, in_ch, out_ch, num_features, dirs, kernel_size, stride, padding, upsample):
        super().__init__()
        self.sdn = SDNLayer(in_ch, 2 * out_ch, num_features, dirs, kernel_size, stride, padding, upsample)
        cnn_module = nn.ConvTranspose2d if upsample else nn.Conv2d
        self.cnn = cnn_module(in_ch, out_ch, kernel_size, stride, padding)

    def forward(self, input):
        cnn_out = self.cnn(input)
        sdn_out, gate = self.sdn(input).chunk(2, 1)
        gate = torch.sigmoid(gate)
        return gate * cnn_out + (1-gate) * sdn_out
