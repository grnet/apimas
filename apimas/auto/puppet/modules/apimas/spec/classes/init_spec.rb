require 'spec_helper'
describe 'apimas' do

  context 'with defaults for all parameters' do
    it { should contain_class('apimas') }
  end
end
