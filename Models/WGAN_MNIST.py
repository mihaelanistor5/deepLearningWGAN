import sys
sys.path.append('/home/karl/文档/Master/02456_Deep_learning/deepLearningWGAN')
import torch
import torch.nn as nn
import os
import numpy as np
from torch.utils.tensorboard import SummaryWriter
from Dataset.MNIST_Data_loader import train_loader
from torchvision import utils

writer = SummaryWriter()
device = 'cuda' if torch.cuda.is_available() else 'cpu'

class Generator(nn.Module):
    def __init__(self, num_input, num_output):
        super(Generator, self).__init__()
        def Conv(input_nums, output_nums):
            layer = []
            layer.append(nn.ConvTranspose2d(input_nums, output_nums, kernel_size=(4,4), stride=(2,2), padding=(1,1)))
            layer.append(nn.BatchNorm2d(output_nums))
            layer.append(nn.ReLU(True))
            return layer

        self.Net = nn.Sequential(
            *Conv(num_input, 1024),
            *Conv(1024, 512),
            *Conv(512, 256),
            nn.ConvTranspose2d(256, 64, kernel_size=(4, 4), stride=(2, 2), padding=(2, 2)),
            nn.BatchNorm2d(64),
            nn.ReLU(True),
            nn.ConvTranspose2d(64, num_output, kernel_size=(4, 4), stride=(2, 2), padding=(1, 1)),
            nn.Tanh()
        )

    def forward(self, input):
        output = self.Net(input)
        return output

class Discriminator(nn.Module):
    def __init__(self, input_nums):
        super(Discriminator, self).__init__()
        def Conv(input_nums, output_nums):
            layer = []
            layer.append(nn.Conv2d(input_nums, output_nums, kernel_size=(4, 4), stride=(2, 2), padding=(1, 1)))
            layer.append(nn.BatchNorm2d(output_nums))
            layer.append(nn.LeakyReLU(0.2, inplace=True))
            return layer

        self.Net = nn.Sequential(
            *Conv(input_nums, 64),
            *Conv(64, 256),
            nn.Conv2d(256, 512, kernel_size=(3, 3), stride=(2, 2), padding=(1, 1)),
            nn.BatchNorm2d(512),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(512, 1, kernel_size=(4, 4), stride=(1, 1), padding=(0, 0)),
        )
        self.Flatten = nn.Flatten()

    def forward(self, input):
        output = self.Net(input)
        return output

class WGAN():
    def __init__(self):
        self.G = Generator(100, 1).to(device)
        self.D = Discriminator(1).to(device)
        self.epochs = int(1e5)
        self.weight_cliping_limit = 0.01
        self.D_iter = 5

    def train(self, train_loader):
        optim_G = torch.optim.RMSprop(self.G.parameters(), lr=5e-5)
        optim_D = torch.optim.RMSprop(self.D.parameters(), lr=5e-5)
        try:
            self.load()
        except:
            pass
        for epoch in range(self.epochs):
            for x, _ in train_loader:
                x = x.to(device)
                batch_size = x.size(0)
                for p in self.D.parameters():
                    p.requires_grad = True
                for i in range(self.D_iter):
                    # train the discreiminator
                    self.D.zero_grad()
                    for p in self.D.parameters():
                        p.data.clamp_(-self.weight_cliping_limit, self.weight_cliping_limit)
                    D_real = self.D(x)
                    loss_real = -D_real.mean(0).view(1)
                    loss_real.backward()
                    optim_D.step()
                    z = torch.randn((batch_size, 100, 1, 1)).to(device)
                    x_fake = self.G(z)
                    loss_fake = self.D(x_fake.detach())
                    loss_fake = loss_fake.mean(0).view(1)
                    loss_fake.backward()
                    optim_D.step()
                    loss_D = loss_fake + loss_real

                z = torch.randn((batch_size, 100, 1, 1)).to(device)
                self.G.zero_grad()
                for p in self.D.parameters():
                    p.requires_grad = False
                x_fake = self.G(z)
                loss_G = self.D(x_fake)
                loss_G = -loss_G.mean(0).view(1)
                # train the generator
                loss_G.backward()
                optim_G.step()
            print("epoch:{}, G_loss:{}".format(epoch, loss_G.cpu().detach().numpy()))
            print("D_real_loss:{}, D_fake_loss:{}".format(loss_real.cpu().detach().numpy(),
                                                                   loss_fake.cpu().detach().numpy()))

            if epoch % 20 == 0:
                self.save(epoch)
                self.evaluate(epoch)

    def save(self, epoch):
        torch.save(self.G.state_dict(), "../checkpoint/WGAN/G.pth")
        torch.save(self.D.state_dict(), "../checkpoint/WGAN/D.pth")
        torch.save(self.G.state_dict(), "../checkpoint/WGAN/G_{}.pth".format(epoch))
        torch.save(self.D.state_dict(), "../checkpoint/WGAN/D_{}.pth".format(epoch))
        print("model saved!")

    def load(self):
        self.G.load_state_dict(torch.load("../checkpoint/WGAN/G.pth"))
        self.D.load_state_dict(torch.load("../checkpoint/WGAN/D.pth"))
        print("model loaded!")

    def evaluate(self, epoch = 0):
        self.load()
        z = torch.randn((1, 100, 1, 1)).to(device)
        with torch.no_grad():
            fake_img = self.G(z)
            fake_img = fake_img.data.cpu()
            grid = utils.make_grid(fake_img)
            utils.save_image(grid, '../Results/WGAN_CIFAR/img_generatori_iter_{}.png'.format(epoch))

if __name__ == '__main__':
    WGAN = WGAN()
    try:
        os.mkdir('../Results/WGAN_CIFAR/')
    except:
        pass
    WGAN.train(train_loader)