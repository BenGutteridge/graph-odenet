# Adapted from https://github.com/rusty1s/pytorch_geometric

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_scatter import scatter_add
from torch_geometric_utils import softmax

class Set2Set(nn.Module):
  r"""The global pooling operator based on iterative content-based attention
  from the `"Order Matters: Sequence to sequence for sets"
  <https://arxiv.org/abs/1511.06391>`_ paper

  .. math::
    \mathbf{q}_t &= \mathrm{LSTM}(\mathbf{q}^{*}_{t-1})

    \alpha_{i,t} &= \mathrm{softmax}(\mathbf{x}_i \cdot \mathbf{q}_t)

    \mathbf{r}_t &= \sum_{i=1}^N \alpha_{i,t} \mathbf{x}_i

    \mathbf{q}^{*}_t &= \mathbf{q}_t \, \Vert \, \mathbf{r}_t,

  where :math:`\mathbf{q}^{*}_T` defines the output of the layer with twice
  the dimensionality as the input.

  Args:
    in_channels (int): Size of each input sample.
    processing_steps (int): Number of iterations :math:`T`.
    num_layers (int, optional): Number of recurrent layers, *.e.g*, setting
      :obj:`num_layers=2` would mean stacking two LSTMs together to form
      a stacked LSTM, with the second LSTM taking in outputs of the first
      LSTM and computing the final results. (default: :obj:`1`)
  """

  def __init__(self, in_channels, processing_steps, num_layers=1):
    super(Set2Set, self).__init__()

    self.in_channels = in_channels
    self.out_channels = 2 * in_channels
    self.processing_steps = processing_steps
    self.num_layers = num_layers

    self.lstm = nn.LSTM(self.out_channels, self.in_channels,
                  num_layers)

    self.reset_parameters()

  def reset_parameters(self):
    self.lstm.reset_parameters()

  def forward(self, x, batch):
    """"""
    batch_size = batch.max().item() + 1

    h = (x.new_zeros((self.num_layers, batch_size, self.in_channels)),
       x.new_zeros((self.num_layers, batch_size, self.in_channels)))
    q_star = x.new_zeros(batch_size, self.out_channels)
    
    one_t = torch.ones_like( batch , dtype=batch.dtype, device=batch.device)
    for i in range(self.processing_steps):
      q, h = self.lstm(q_star.unsqueeze(0), h)
      q = q.view(batch_size, self.in_channels)
      e = (x * q[batch]).sum(dim=-1, keepdim=True)
      # Softmax
      a = torch.zeros( [x.size()[0]], dtype=x.dtype, device=x.device )
      for i in range(batch_size):
        mask = batch.eq(one_t*i)
        elements_to_softmax = torch.masked_select( e.squeeze(-1), mask )
        softmaxed_elements = F.softmax(elements_to_softmax, dim=0 )
        a[mask] += softmaxed_elements
      #end for
      a = a.unsqueeze(1)
      r = scatter_add(a * x, batch, dim=0, dim_size=batch_size)
      q_star = torch.cat([q, r], dim=-1)
     #end for

    return q_star


  def __repr__(self):
    return '{}({}, {})'.format(self.__class__.__name__, self.in_channels,
                   self.out_channels)

class Set2Set__UNUSED(nn.Module):
  r"""The global pooling operator based on iterative content-based attention
  from the `"Order Matters: Sequence to sequence for sets"
  <https://arxiv.org/abs/1511.06391>`_ paper

  .. math::
    \mathbf{q}_t &= \mathrm{LSTM}(\mathbf{q}^{*}_{t-1})

    \alpha_{i,t} &= \mathrm{softmax}(\mathbf{x}_i \cdot \mathbf{q}_t)

    \mathbf{r}_t &= \sum_{i=1}^N \alpha_{i,t} \mathbf{x}_i

    \mathbf{q}^{*}_t &= \mathbf{q}_t \, \Vert \, \mathbf{r}_t,

  where :math:`\mathbf{q}^{*}_T` defines the output of the layer with twice
  the dimensionality as the input.

  Args:
    in_channels (int): Size of each input sample.
    processing_steps (int): Number of iterations :math:`T`.
    num_layers (int, optional): Number of recurrent layers, *.e.g*, setting
      :obj:`num_layers=2` would mean stacking two LSTMs together to form
      a stacked LSTM, with the second LSTM taking in outputs of the first
      LSTM and computing the final results. (default: :obj:`1`)
  """

  def __init__(self, in_channels, processing_steps, num_layers=1):
    raise NotImplementedError( "This model's implementation does an inplace operation that doesn't allow backpropagation" )
    super(Set2Set__UNUSED, self).__init__()

    self.in_channels = in_channels
    self.out_channels = 2 * in_channels
    self.processing_steps = processing_steps
    self.num_layers = num_layers

    self.lstm = nn.LSTM(self.out_channels, self.in_channels,
                  num_layers)

    self.reset_parameters()

  def reset_parameters(self):
    self.lstm.reset_parameters()

  def forward(self, x, batch):
    """"""
    batch_size = batch.max().item() + 1

    h = (x.new_zeros((self.num_layers, batch_size, self.in_channels)),
       x.new_zeros((self.num_layers, batch_size, self.in_channels)))
    q_star = x.new_zeros(batch_size, self.out_channels)
    
    if not x.is_cuda: # CPU ver
      for i in range(self.processing_steps):
        q, h = self.lstm(q_star.unsqueeze(0), h)
        q = q.view(batch_size, self.in_channels)
        e = (x * q[batch]).sum(dim=-1, keepdim=True)
        a = softmax(e, batch, num_nodes=batch_size)
        
        r = scatter_add(a * x, batch, dim=0, dim_size=batch_size)
        q_star = torch.cat([q, r], dim=-1)
       #end for
    else: # CUDA version
      a = torch.zeros( [x.size()[0],1], dtype=x.dtype, device=x.device )
      one_t = torch.ones_like( batch , dtype=batch.dtype, device=batch.device)
      for i in range(self.processing_steps):
        q, h = self.lstm(q_star.unsqueeze(0), h)
        q = q.view(batch_size, self.in_channels)
        e = (x * q[batch]).sum(dim=-1, keepdim=True)
        # Softmax
        for i in range(batch_size):
          mask = batch.eq(one_t*i)
          elements_to_softmax = torch.masked_select( e.squeeze(), mask )
          softmaxed_elements = F.softmax(elements_to_softmax, dim=0 ).unsqueeze(1)
          a[mask] = softmaxed_elements
        #end for
        
        r = scatter_add(a * x, batch, dim=0, dim_size=batch_size)
        q_star = torch.cat([q, r], dim=-1)
       #end for
     #end if-else

    return q_star


  def __repr__(self):
    return '{}({}, {})'.format(self.__class__.__name__, self.in_channels,
                   self.out_channels)

