# Taken and adapted from http://rusty1s.github.io/pytorch_scatter
import torch
from torch.autograd import Function
from itertools import repeat


def maybe_dim_size(index, dim_size=None):
    if dim_size is not None:
        return dim_size
    return index.max().item() + 1 if index.numel() > 0 else 0


def gen(src, index, dim=-1, out=None, dim_size=None, fill_value=0):
    dim = range(src.dim())[dim]  # Get real dim value.

    # Automatically expand index tensor to the right dimensions.
    if index.dim() == 1:
        index_size = list(repeat(1, src.dim()))
        index_size[dim] = src.size(dim)
        index = index.view(index_size).expand_as(src)

    # Generate output tensor if not given.
    if out is None:
        out_size = list(src.size())
        dim_size = maybe_dim_size(index, dim_size)
        out_size[dim] = dim_size
        out = src.new_full(out_size, fill_value)

    return src, out, index, dim
    
def scatter_max_manual(src,index,out,arg,dim):
    raise NotImplementedError()
    """
    for i in range(index.size(dim)):
        idx = index_data[i * index_stride]
        if src_data[i * src_stride] >= out_data[idx * out_stride]):
            out_data[idx * out_stride] = src_data[i * src_stride]
            arg_data[idx * arg_stride] = i
    """
    
    
def get_func(name, tensor):
    if tensor.is_cuda:
        module = torch_scatter.scatter_cuda
    else:
        module = torch_scatter.scatter_cpu
    return getattr(module, name)


def scatter_add(src, index, dim=-1, out=None, dim_size=None, fill_value=0):
    r"""
    |
    .. image:: https://raw.githubusercontent.com/rusty1s/pytorch_scatter/
            master/docs/source/_figures/add.svg?sanitize=true
        :align: center
        :width: 400px
    |
    Sums all values from the :attr:`src` tensor into :attr:`out` at the indices
    specified in the :attr:`index` tensor along a given axis :attr:`dim`. For
    each value in :attr:`src`, its output index is specified by its index in
    :attr:`input` for dimensions outside of :attr:`dim` and by the
    corresponding value in :attr:`index` for dimension :attr:`dim`. If
    multiple indices reference the same location, their **contributions add**.
    Formally, if :attr:`src` and :attr:`index` are n-dimensional tensors with
    size :math:`(x_0, ..., x_{i-1}, x_i, x_{i+1}, ..., x_{n-1})` and
    :attr:`dim` = `i`, then :attr:`out` must be an n-dimensional tensor with
    size :math:`(x_0, ..., x_{i-1}, y, x_{i+1}, ..., x_{n-1})`. Moreover, the
    values of :attr:`index` must be between `0` and `out.size(dim) - 1`.
    For one-dimensional tensors, the operation computes
    .. math::
        \mathrm{out}_i = \mathrm{out}_i + \sum_j \mathrm{src}_j
    where :math:`\sum_j` is over :math:`j` such that
    :math:`\mathrm{index}_j = i`.
    Args:
        src (Tensor): The source tensor.
        index (LongTensor): The indices of elements to scatter.
        dim (int, optional): The axis along which to index.
            (default: :obj:`-1`)
        out (Tensor, optional): The destination tensor. (default: :obj:`None`)
        dim_size (int, optional): If :attr:`out` is not given, automatically
            create output with size :attr:`dim_size` at dimension :attr:`dim`.
            If :attr:`dim_size` is not given, a minimal sized output tensor is
            returned. (default: :obj:`None`)
        fill_value (int, optional): If :attr:`out` is not given, automatically
            fill output tensor with :attr:`fill_value`. (default: :obj:`0`)
    :rtype: :class:`Tensor`
    .. testsetup::
        import torch
    .. testcode::
        from torch_scatter import scatter_add
        src = torch.Tensor([[2, 0, 1, 4, 3], [0, 2, 1, 3, 4]])
        index = torch.tensor([[4, 5, 4, 2, 3], [0, 0, 2, 2, 1]])
        out = src.new_zeros((2, 6))
        out = scatter_add(src, index, out=out)
        print(out)
    .. testoutput::
       tensor([[0, 0, 4, 3, 3, 0],
               [2, 4, 4, 0, 0, 0]])
    """
    src, out, index, dim = gen(src, index, dim, out, dim_size, fill_value)
    return out.scatter_add_(dim, index, src)


class ScatterMax(Function):
    @staticmethod
    def forward(ctx, out, src, index, dim):
        arg = index.new_full(out.size(), -1)
        func = scatter_max_manual#get_func('scatter_max', src)
        func(src, index, out, arg, dim)

        ctx.mark_dirty(out)
        ctx.dim = dim
        ctx.save_for_backward(index, arg)

        return out, arg

    @staticmethod
    def backward(ctx, grad_out, grad_arg):
        index, arg = ctx.saved_tensors

        grad_src = None
        if ctx.needs_input_grad[1]:
            grad_src = grad_out.new_zeros(index.size())
            func = scatter_max_manual#get_func('index_backward', grad_out)
            func(grad_out, index, arg, grad_src, ctx.dim)

        return None, grad_src, None, None


def scatter_max(src, index, dim=-1, out=None, dim_size=None, fill_value=None):
    r"""
    |
    .. image:: https://raw.githubusercontent.com/rusty1s/pytorch_scatter/
            master/docs/source/_figures/max.svg?sanitize=true
        :align: center
        :width: 400px
    |
    Maximizes all values from the :attr:`src` tensor into :attr:`out` at the
    indices specified in the :attr:`index` tensor along a given axis
    :attr:`dim`.If multiple indices reference the same location, their
    **contributions maximize** (`cf.` :meth:`~torch_scatter.scatter_add`).
    The second return tensor contains index location in :attr:`src` of each
    maximum value (known as argmax).
    For one-dimensional tensors, the operation computes
    .. math::
        \mathrm{out}_i = \max(\mathrm{out}_i, \max_j(\mathrm{src}_j))
    where :math:`\max_j` is over :math:`j` such that
    :math:`\mathrm{index}_j = i`.
    Args:
        src (Tensor): The source tensor.
        index (LongTensor): The indices of elements to scatter.
        dim (int, optional): The axis along which to index.
            (default: :obj:`-1`)
        out (Tensor, optional): The destination tensor. (default: :obj:`None`)
        dim_size (int, optional): If :attr:`out` is not given, automatically
            create output with size :attr:`dim_size` at dimension :attr:`dim`.
            If :attr:`dim_size` is not given, a minimal sized output tensor is
            returned. (default: :obj:`None`)
        fill_value (int, optional): If :attr:`out` is not given, automatically
            fill output tensor with :attr:`fill_value`. If set to :obj:`None`,
            the output tensor is filled with the smallest possible value of
            :obj:`src.dtype`. (default: :obj:`None`)
    :rtype: (:class:`Tensor`, :class:`LongTensor`)
    .. testsetup::
        import torch
    .. testcode::
        from torch_scatter import scatter_max
        src = torch.Tensor([[2, 0, 1, 4, 3], [0, 2, 1, 3, 4]])
        index = torch.tensor([[4, 5, 4, 2, 3], [0, 0, 2, 2, 1]])
        out = src.new_zeros((2, 6))
        out, argmax = scatter_max(src, index, out=out)
        print(out)
        print(argmax)
    .. testoutput::
       tensor([[0, 0, 4, 3, 2, 0],
               [2, 4, 3, 0, 0, 0]])
       tensor([[-1, -1,  3,  4,  0,  1],
               [ 1,  4,  3, -1, -1, -1]])
    """
    if fill_value is None:
        op = torch.finfo if torch.is_floating_point(src) else torch.iinfo
        fill_value = op(src.dtype).min
    src, out, index, dim = gen(src, index, dim, out, dim_size, fill_value)
    if src.size(dim) == 0:  # pragma: no cover
        return out, index.new_full(out.size(), -1)
    return ScatterMax.apply(out, src, index, dim)
